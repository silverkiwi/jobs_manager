import logging

from typing import Dict, Any

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import UpdateView, TemplateView
from django_tables2 import SingleTableView
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.db import transaction
from django.utils import timezone

from xero_python.accounting import AccountingApi
from apps.workflow.api.xero.reprocess_xero import set_client_fields
from apps.workflow.api.xero.sync import (
    single_sync_client,
    sync_client_to_xero,
    serialise_xero_object,
    sync_clients,
    sync_xero_clients_only,
    delete_clients_from_xero,
    archive_clients_in_xero,
)
from apps.workflow.api.xero.xero import get_valid_token, api_client, get_tenant_id
from apps.accounting.models import Invoice, Bill

from apps.client.models import Client, ClientContact
from apps.client.forms import ClientForm
from apps.client.serializers import ClientContactSerializer

from apps.job.models import Job

logger = logging.getLogger(__name__)


# Updated view function to get contact persons for a client from model fields
def get_client_contact_persons(request, client_id):
    """
    API endpoint to retrieve contact persons for a specific client
    from the structured fields in the Client model.
    """
    try:
        client = get_object_or_404(Client, id=client_id)
        contact_persons_data = []
        processed_contacts = set()  # To avoid duplicates

        logger.debug(
            f"Fetching contact persons for client ID: {client_id} from model fields."
        )

        # Add primary contact if available
        if client.primary_contact_name:
            primary_contact = {
                "name": client.primary_contact_name,
                "email": client.primary_contact_email or "",
            }
            contact_tuple = (primary_contact["name"], primary_contact["email"])
            if contact_tuple not in processed_contacts:
                contact_persons_data.append(primary_contact)
                processed_contacts.add(contact_tuple)
                logger.debug(f"Added primary contact: {primary_contact}")

        # Add additional contact persons
        if client.additional_contact_persons and isinstance(
            client.additional_contact_persons, list
        ):
            for person_dict in client.additional_contact_persons:
                if isinstance(person_dict, dict) and person_dict.get("name"):
                    additional_contact = {
                        "name": person_dict["name"],
                        "email": person_dict.get("email", ""),
                    }
                    contact_tuple = (
                        additional_contact["name"],
                        additional_contact["email"],
                    )
                    # Only add if it's not the same as the primary contact already added
                    # or if it's a distinct additional contact.
                    if contact_tuple not in processed_contacts:
                        contact_persons_data.append(additional_contact)
                        processed_contacts.add(contact_tuple)
                        logger.debug(f"Added additional contact: {additional_contact}")
                else:
                    logger.warning(
                        f"Skipping invalid item in additional_contact_persons for client {client_id}: {person_dict}"
                    )

        logger.info(
            f"Successfully retrieved {len(contact_persons_data)} contact persons for client {client_id} from model."
        )
        return JsonResponse(contact_persons_data, safe=False)

    except Exception as e:
        logger.error(
            f"Error fetching contact persons for client {client_id} from model: {str(e)}",
            exc_info=True,
        )
        return JsonResponse(
            {
                "success": False,
                "message": "Failed to retrieve contact persons",
                "details": str(e),
            },
            status=500,
        )


def get_client_phones(request, client_id):
    """
    API endpoint to retrieve all phone numbers for a specific client
    from the Client model.
    """
    try:
        client = get_object_or_404(Client, id=client_id)
        phones_data = []

        logger.debug(
            f"Fetching phone numbers for client ID: {client_id} from model field 'all_phones'."
        )

        if client.all_phones and isinstance(client.all_phones, list):
            for phone_entry in client.all_phones:
                if isinstance(phone_entry, dict) and phone_entry.get("number"):
                    phones_data.append(
                        {
                            "type": phone_entry.get("type", "N/A"),
                            "number": phone_entry["number"],
                        }
                    )

        # Optionally, add the main client.phone if it's not already in all_phones
        # For simplicity, we'll assume all_phones is comprehensive for now.

        logger.info(
            f"Successfully retrieved {len(phones_data)} phone numbers for client {client_id} from model."
        )
        return JsonResponse(phones_data, safe=False)

    except Exception as e:
        logger.error(
            f"Error fetching phone numbers for client {client_id} from model: {str(e)}",
            exc_info=True,
        )
        return JsonResponse(
            {"error": "Failed to retrieve phone numbers", "details": str(e)}, status=500
        )


def get_all_clients_api(request):
    """
    API endpoint to retrieve all clients.
    Returns a list of clients with their ID and name.
    """
    try:
        clients = Client.objects.all().order_by("name")
        clients_data = []
        for client in clients:
            clients_data.append(
                {
                    "id": str(client.id),  # Convert UUID to string
                    "name": client.name,
                    "xero_contact_id": client.xero_contact_id,  # Might be useful
                }
            )
        logger.info(f"Successfully retrieved {len(clients_data)} clients for API.")
        return JsonResponse(clients_data, safe=False)
    except Exception as e:
        logger.error(f"Error fetching all clients for API: {str(e)}", exc_info=True)
        return JsonResponse(
            {"error": "Failed to retrieve clients", "details": str(e)}, status=500
        )


class ClientListView(SingleTableView):
    model = Client
    template_name = "clients/list_clients.html"
    # table_class = ClientTable
    # context_object_name = "clients"


class ClientUpdateView(UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/update_client.html"
    success_url = reverse_lazy("list_clients")

    def form_valid(self, form):
        response = super().form_valid(form)

        # Simple token check before attempting sync
        token = get_valid_token()
        if not token:
            messages.warning(self.request, "Xero authentication required.")
            return redirect("api_xero_authenticate")

        try:
            sync_client_to_xero(self.object)
            messages.success(self.request, "Client synced to Xero successfully")
        except Exception as e:
            messages.error(self.request, "Failed to sync to Xero")
            return render(
                self.request,
                "general/generic_error.html",
                {"error_message": f"Failed to sync client to Xero: {str(e)}"},
            )

        return response


def ClientSearch(request):
    query = request.GET.get("q", "")
    if query and len(query) >= 3:  # Only search when the query is 3+ characters
        clients = Client.objects.filter(Q(name__icontains=query))[:10]
        results = [
            {
                "id": client.id,
                "name": client.name,
                "email": client.email or "",
                "phone": client.phone or "",
                "address": client.address or "",
                "is_account_customer": client.is_account_customer,
                "xero_contact_id": client.xero_contact_id or "",
                "last_invoice_date": (
                    client.get_last_invoice_date().strftime("%d/%m/%Y")
                    if client.get_last_invoice_date()
                    else ""
                ),
                "total_spend": f"${client.get_total_spend():,.2f}",
                "raw_json": client.raw_json,
            }
            for client in clients
        ]
    else:
        results = []

    return JsonResponse({"results": results})


def client_detail(request):
    """
    API endpoint to return detailed client information including raw_json.
    """
    client_id = request.GET.get("id", "")
    if not client_id:
        return JsonResponse({"error": "Client ID is required"}, status=400)

    try:
        client = Client.objects.get(id=client_id)
        client_data = {
            "id": client.id,
            "name": client.name,
            "email": client.email or "",
            "phone": client.phone or "",
            "address": client.address or "",
            "is_account_customer": client.is_account_customer,
            "xero_contact_id": client.xero_contact_id or "",
            "raw_json": client.raw_json,
        }
        return JsonResponse({"client": client_data})
    except Client.DoesNotExist:
        return JsonResponse({"error": "Client not found"}, status=404)
    except Exception as e:
        logger.error(f"Error fetching client details: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


def all_clients(request):
    """
    API endpoint to return all clients as JSON for AJAX table population.
    """
    clients = Client.objects.values(
        "id", "name", "email", "phone", "address", "is_account_customer"
    )
    return JsonResponse(list(clients), safe=False)


def AddClient(request):
    # Check for valid Xero token first
    token = get_valid_token()
    if not token:
        messages.add_message(
            request,
            messages.WARNING,
            "Xero authentication required",
            extra_tags="warning",
        )
        # Store the current URL with query parameters to return to after auth
        return_url = (
            f"{request.path}?{request.GET.urlencode()}" if request.GET else request.path
        )
        return redirect(f"{reverse_lazy('api_xero_authenticate')}?next={return_url}")
    if request.method == "GET":
        # Sync clients from Xero before displaying the form
        # Otherwise we try and create clients only to discover they already exist too much
        sync_xero_clients_only()

        name = request.GET.get("name", "")
        form = ClientForm(initial={"name": name}) if name else ClientForm()
        return render(request, "client/add_client.html", {"form": form})

    elif request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            # Create in Xero first
            accounting_api = AccountingApi(api_client)
            xero_tenant_id = get_tenant_id()

            try:
                # Log the form data
                logger.debug("Form cleaned data: %s", form.cleaned_data)

                # Check if contact already exists
                existing_contacts = accounting_api.get_contacts(
                    xero_tenant_id, where=f'Name="{form.cleaned_data["name"]}"'
                )

                if existing_contacts and existing_contacts.contacts:
                    # Return error response for duplicate client
                    logger.info(
                        "Found existing contact with name: %s",
                        form.cleaned_data["name"],
                    )

                    error_details = {
                        "error_type": "DuplicateClientError",
                        "name": form.cleaned_data["name"],
                        "email": form.cleaned_data.get("email", ""),
                    }

                    # Get client info from existing contact
                    xero_client = existing_contacts.contacts[0]
                    xero_contact_id = getattr(xero_client, "contact_id", "")

                    # Return error with the existing client info
                    return JsonResponse(
                        {
                            "success": False,
                            "error": f"Client '{form.cleaned_data['name']}' already exists in Xero",
                            "error_details": error_details,
                            "existing_client": {
                                "name": form.cleaned_data["name"],
                                "xero_contact_id": xero_contact_id,
                            },
                        },
                        status=409,
                    )  # 409 Conflict status code
                else:
                    # Create new contact in Xero
                    contact_data = {
                        "name": form.cleaned_data["name"],
                        "emailAddress": form.cleaned_data["email"] or "",
                        "phones": [
                            {
                                "phoneType": "DEFAULT",
                                "phoneNumber": form.cleaned_data["phone"] or "",
                            }
                        ],
                        "addresses": [
                            {
                                "addressType": "STREET",
                                "addressLine1": form.cleaned_data["address"] or "",
                            }
                        ],
                        "isCustomer": form.cleaned_data["is_account_customer"],
                    }
                    logger.debug("Xero contact data: %s", contact_data)

                    response = accounting_api.create_contacts(
                        xero_tenant_id, contacts={"contacts": [contact_data]}
                    )

                # Log and validate response
                logger.debug("Xero API response: %s", response)

                if not response:
                    raise ValueError("No response received from Xero")

                if not hasattr(response, "contacts") or not response.contacts:
                    raise ValueError("No contact data in Xero response")

                if len(response.contacts) != 1:
                    raise ValueError(
                        f"Expected 1 contact in response, got {len(response.contacts)}"
                    )

                # Use sync_clients to create local client from Xero data
                client_instances = sync_clients(response.contacts)
                if not client_instances:
                    raise ValueError("Failed to sync client from Xero")

                # Get the created client
                created_client = client_instances[0]

                # Return JSON response with the created client data and success flag
                return JsonResponse(
                    {
                        "success": True,
                        "client": {
                            "id": str(created_client.id),
                            "name": created_client.name,
                            "xero_contact_id": created_client.xero_contact_id or "",
                        },
                    }
                )

            except Exception as e:
                error_msg = f"Failed to create client in Xero: {str(e)}"
                logger.error(error_msg, exc_info=True)

                # Create error details object
                error_details = {
                    "error_type": type(e).__name__,
                    "name": form.cleaned_data.get("name", ""),
                    "email": form.cleaned_data.get("email", ""),
                }

                return JsonResponse(
                    {
                        "success": False,
                        "error": error_msg,
                        "error_details": error_details,
                    },
                    status=400,
                )
        else:
            # Form is invalid
            errors = form.errors.as_json()

            # Create error details for form validation errors
            error_details = {
                "error_type": "FormValidationError",
                "name": (
                    form.cleaned_data.get("name", "")
                    if hasattr(form, "cleaned_data")
                    else ""
                ),
                "email": (
                    form.cleaned_data.get("email", "")
                    if hasattr(form, "cleaned_data")
                    else ""
                ),
            }

            return JsonResponse(
                {
                    "success": False,
                    "error": "Form validation failed",
                    "form_errors": errors,
                    "error_details": error_details,
                },
                status=400,
            )


class UnusedClientsView(TemplateView):
    """
    View for managing unused Xero clients.
    Lists and allows bulk deletion of clients that have no invoices or bills.
    """

    template_name = "client/unused_clients.html"
    items_per_page = 50

    def get_unused_clients(self):
        """
        Get queryset of clients with no jobs, invoices, or bills.
        Excludes clients that are already archived in Xero.
        Returns clients ordered by creation date.

        Note: We use set operations instead of exclude(Q()) because:
        1. Foreign key fields (client_id) might contain NULL values
        2. SQL exclude with OR conditions can behave unexpectedly with NULLs
        3. Set operations on actual IDs are more reliable for this use case
        """
        clients_with_invoices = set(
            Invoice.objects.values_list("client_id", flat=True).distinct()
        )
        clients_with_bills = set(
            Bill.objects.values_list("client_id", flat=True).distinct()
        )
        clients_with_jobs = set(
            Job.objects.values_list("client_id", flat=True).distinct()
        )

        logger.debug(f"Found {len(clients_with_invoices)} clients with invoices")
        logger.debug(f"Found {len(clients_with_bills)} clients with bills")
        logger.debug(f"Found {len(clients_with_jobs)} clients with jobs")

        # Get all client IDs
        all_client_ids = set(Client.objects.values_list("id", flat=True))
        logger.debug(f"Total clients: {len(all_client_ids)}")

        # Find clients that don't appear in any of the above sets
        used_client_ids = clients_with_invoices | clients_with_bills | clients_with_jobs
        unused_client_ids = all_client_ids - used_client_ids
        logger.debug(f"Found {len(unused_client_ids)} unused clients")

        return Client.objects.filter(id__in=unused_client_ids).order_by(
            "django_created_at"
        )

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """
        Add pagination and client data to the template context.
        """
        context = super().get_context_data(**kwargs)
        page = self.request.GET.get("page", 1)

        unused_clients = self.get_unused_clients()
        paginator = Paginator(unused_clients, self.items_per_page)
        page_obj = paginator.get_page(page)

        unused_clients_data = [
            {
                "id": client.id,
                "name": client.name,
                "created_at": timezone.localtime(client.django_created_at).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "email": client.email or "",
                "phone": client.phone or "",
            }
            for client in page_obj
        ]

        context.update(
            {
                "unused_clients": unused_clients_data,
                "page_obj": page_obj,
                "total_count": paginator.count,
                "items_per_page": self.items_per_page,
            }
        )
        return context

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs) -> JsonResponse:
        """
        Handle bulk deletion of unused clients.
        Archives the contacts in Xero and deletes them from our database.
        """
        try:
            client_ids = request.POST.getlist("client_ids[]")
            if not client_ids:
                return JsonResponse(
                    {"success": False, "error": "No clients selected"}, status=400
                )

            clients_to_delete = self.get_unused_clients().filter(id__in=client_ids)
            deletion_count = clients_to_delete.count()

            with transaction.atomic():
                try:
                    # Archive in Xero first
                    success_count, error_count = archive_clients_in_xero(
                        clients_to_delete
                    )
                    if error_count > 0:
                        raise Exception(
                            f"Failed to archive {error_count} clients in Xero"
                        )

                    # If archiving succeeded, delete from our database
                    clients_to_delete.delete()
                except Exception as e:
                    logger.error(f"Failed to archive/delete clients: {str(e)}")
                    return JsonResponse(
                        {
                            "success": False,
                            "error": f"Failed to archive/delete clients: {str(e)}",
                        },
                        status=500,
                    )

            logger.info(
                f"Successfully archived and deleted {deletion_count} unused clients"
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": f"Successfully archived and deleted {deletion_count} clients",
                    "deleted_count": deletion_count,
                }
            )

        except Exception as e:
            logger.error(f"Error in bulk client deletion: {str(e)}")
            return JsonResponse({"success": False, "error": str(e)}, status=500)


# API views for ClientContact management
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def get_client_contacts_api(request, client_id):
    """
    API endpoint to retrieve all contacts for a specific client.
    """
    try:
        client = get_object_or_404(Client, id=client_id)
        contacts = ClientContact.objects.filter(client=client).order_by('-is_primary', 'name')
        serializer = ClientContactSerializer(contacts, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching contacts for client {client_id}: {str(e)}")
        return Response(
            {"error": f"Error fetching contacts: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def create_client_contact_api(request):
    """
    API endpoint to create a new contact for a client.
    """
    try:
        serializer = ClientContactSerializer(data=request.data)
        if serializer.is_valid():
            contact = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error creating contact: {str(e)}")
        return Response(
            {"error": f"Error creating contact: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'PUT', 'DELETE'])
def client_contact_detail_api(request, contact_id):
    """
    API endpoint to retrieve, update, or delete a specific contact.
    """
    contact = get_object_or_404(ClientContact, id=contact_id)
    
    if request.method == 'GET':
        serializer = ClientContactSerializer(contact)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = ClientContactSerializer(contact, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        contact.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
