from datetime import datetime, timedelta
from decimal import Decimal
import logging
import uuid
import traceback
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from xero_python.accounting import AccountingApi
from xero_python.identity import IdentityApi
from xero_python.accounting.models import (
    Invoice as XeroInvoice,
    LineItem,
    Contact,
)
from xero_python.exceptions import AccountingBadRequestException

from workflow.api.xero.sync import synchronise_xero_data
from workflow.api.xero.xero import (
    api_client,
    exchange_code_for_token,
    get_authentication_url,
    get_token,
    refresh_token,
    get_tenant_id,
)
from workflow.models import Job, Invoice, InvoiceLineItem

logger = logging.getLogger("xero")


# Xero Authentication (Step 1: Redirect user to Xero OAuth2 login)
def xero_authenticate(request: HttpRequest) -> HttpResponse:
    state = str(uuid.uuid4())
    request.session["oauth_state"] = state
    authorization_url = get_authentication_url(state)
    return redirect(authorization_url)


# OAuth callback
def xero_oauth_callback(request: HttpRequest) -> HttpResponse:
    code = request.GET.get("code")
    state = request.GET.get("state")
    session_state = request.session.get("oauth_state")

    result = exchange_code_for_token(code, state, session_state)

    if "error" in result:
        return render(
            request, "xero/error_xero_auth.html", {"error_message": result["error"]}
        )

    return redirect("refresh_xero_data")


# Refresh OAuth token and handle redirects
def refresh_xero_token(request: HttpRequest) -> HttpResponse:
    refreshed_token = refresh_token()

    if not refreshed_token:
        return redirect("xero_authenticate")

    return redirect("xero_get_contacts")


# Xero connection success view
def success_xero_connection(request: HttpRequest) -> HttpResponse:
    return render(request, "xero/success_xero_connection.html")


def refresh_xero_data(request):
    try:
        token = get_token()

        if not token:
            logger.info(
                "User is not authenticated with Xero, redirecting to authentication"
            )
            return redirect(
                "authenticate_xero"
            )  # Redirect to the Xero authentication path

        # If authenticated, proceed with syncing data
        synchronise_xero_data()
        logger.info("Xero data successfully refreshed")

    except Exception as e:
        if "token" in str(e).lower():  # Or check for the specific error code
            logger.error(f"Error while refreshing Xero data: {str(e)}")
            return redirect("authenticate_xero")
        else:
            logger.error(f"Error while refreshing Xero data: {str(e)}")
            traceback.print_exc()
            return render(
                request, "general/generic_error.html", {"error_message": str(e)}
            )

    # After successful sync, redirect to the home page or wherever appropriate
    return redirect("/")


def create_xero_invoice(job_id):
    try:
        job = Job.objects.get(id=job_id)

        if not job.client:
            raise ValueError("Job does not have a client")

        client = job.client
        if not client.validate_for_xero():
            raise ValueError("Client data is not valid for Xero")

        invoice = Invoice.objects.create(
            client=client,
            date=datetime.now().date(),
            due_date=(datetime.now().date() + timedelta(days=30)),
            status="Draft",
            total_excl_tax=Decimal("0.00"),
            tax=Decimal("0.00"),
            total_incl_tax=Decimal("0.00"),
            amount_due=Decimal("0.00"),
            xero_last_modified=datetime.now(),
            raw_json={},
        )

        line_items_data = [
            {
                "description": "Total Time",
                "quantity": 1,
                "unit_price": job.latest_reality_pricing.total_time_cost
                or Decimal("0.00"),
            },
            {
                "description": "Total Materials",
                "quantity": 1,
                "unit_price": job.latest_reality_pricing.total_material_cost
                or Decimal("0.00"),
            },
            {
                "description": "Total Adjustments",
                "quantity": 1,
                "unit_price": job.latest_reality_pricing.total_adjustments_cost
                or Decimal("0.00"),
            },
        ]

        total_excl_tax = Decimal("0.00")
        xero_line_items = []
        for item_data in line_items_data:
            line_item = InvoiceLineItem.objects.create(
                invoice=invoice,
                description=item_data["description"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                line_amount_excl_tax=item_data["unit_price"] * item_data["quantity"],
                line_amount_incl_tax=item_data["unit_price"] * item_data["quantity"],
                tax_amount=Decimal("0.00"),
            )
            total_excl_tax += line_item.line_amount_excl_tax
            xero_line_items.append(
                LineItem(
                    description=item_data["description"],
                    quantity=item_data["quantity"],
                    unit_amount=item_data["unit_price"],
                    tax_type="NONE",  # Need to adjust if there's taxes
                )
            )

        invoice.total_excl_tax = total_excl_tax
        invoice.total_incl_tax = (
            total_excl_tax  # Again, need to adjust if there's taxes
        )
        invoice.amount_due = (
            total_excl_tax  # Need to adjust if there's parcial payments
        )
        invoice.save()

        xero_tenant_id = get_tenant_id()
        xero_api = AccountingApi(api_client())

        xero_contact = Contact(contact_id=client.xero_contact_id)

        xero_invoice = XeroInvoice(
            type="ACCREC",
            contact=xero_contact,
            line_items=xero_line_items,
            date=datetime.now().date(),
            due_date=(datetime.now().date() + timedelta(days=30)),
            line_amount_types="Exclusive",
        )

        response = xero_api.create_invoices(xero_tenant_id, [xero_invoice])

        if response and response.invoices:
            invoice.raw_json = response.to_dict()
            invoice.xero_id = response.invoices[0].invoice_id
            invoice.save()

        logger.info(f"Invoice {invoice.id} created successfully for job {job_id}")
        return JsonResponse({
            "success": True,
            "invoice_id": invoice.id,
            "xero_id": invoice.xero_id,
            "client": invoice.client.name,
            "total_excl_tax": str(invoice.total_excl_tax),
            "total_incl_tax": str(invoice.total_incl_tax),
        })

    except AccountingBadRequestException as e:
        logger.error(f"Error creating invoice in Xero: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Job.DoesNotExist:
        return JsonResponse({"success": False, "error": "Job not found."}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


class XeroIndexView(TemplateView):
    """Note this page is currently inaccessible.  We are using a dropdown menu instead.
    Kept as of 2025-01-07 in case we change our mind"""

    template_name = "xero_index.html"
