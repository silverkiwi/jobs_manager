import logging

from django import forms
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django_tables2 import SingleTableView

from workflow.api.xero.sync import sync_client_to_xero, single_sync_client
from workflow.forms import ClientForm
from workflow.models import Client

# from workflow.tables import ClientTable

logger = logging.getLogger(__name__)


class ClientListView(SingleTableView):
    model = Client
    # table_class = ClientTable
    template_name = "clients/list_clients.html"


class ClientUpdateView(UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/update_client.html"
    success_url = reverse_lazy("list_clients")


def ClientSearch(request):
    query = request.GET.get("q", "")
    if query and len(query) >= 3:  # Only search when the query is 3+ characters
        clients = Client.objects.filter(Q(name__icontains=query))[
            :10
        ]  # Adjust fields as needed
        results = [{"id": client.id, "name": client.name} for client in clients]
    else:
        results = []

    return JsonResponse({"results": results})


def AddClient(request):
    if request.method == "GET":
        name = request.GET.get("name", "")
        form = ClientForm(initial={"name": name}) if name else ClientForm()
        return render(request, "clients/add_client.html", {"form": form})

    elif request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            client = Client(
                name=form.cleaned_data["name"],
                email=form.cleaned_data["email"],
                phone=form.cleaned_data["phone"],
                address=form.cleaned_data["address"],
            )
            client.save()

            # Try syncing with Xero and catch any potential errors
            try:
                sync_client_to_xero(client)
                single_sync_client(client_identifier=client.id, delete_local=False)
                # Success: Render the success template that closes the tab
                return render(request, "clients/client_added_success.html")
            except Exception as e:
                # Xero sync failed: Log the error and render a failure message
                logger.error(f"Failed to sync client {client.name} to Xero: {str(e)}")
                return render(
                    request, "clients/client_added_failure.html", {"error": str(e)}
                )
        else:
            return render(request, "clients/add_client.html", {"form": form})
