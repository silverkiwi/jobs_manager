import logging

from django import forms
from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django_tables2 import SingleTableView

from workflow.forms import ClientForm
from workflow.models import Client
# from workflow.tables import ClientTable

logger = logging.getLogger(__name__)


class ClientListView(SingleTableView):
    model = Client
    # table_class = ClientTable
    template_name = "workflow/list_clients.html"


class ClientUpdateView(UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "workflow/update_client.html"
    success_url = reverse_lazy("list_clients")
