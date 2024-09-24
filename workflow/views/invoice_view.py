import logging

from django import forms
from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django_tables2 import SingleTableView

from workflow.filters import InvoiceFilter
from workflow.forms import InvoiceForm
from workflow.models import Invoice
from workflow.tables import InvoiceTable

logger = logging.getLogger(__name__)


class InvoiceListView(SingleTableView):
    model = Invoice
    table_class = InvoiceTable
    template_name = "workflow/invoices/list_invoices.html"
    filterset_class = InvoiceFilter

    def get_queryset(self):
        # Apply the filter to the queryset
        queryset = super().get_queryset()
        self.filterset = self.filterset_class(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset  # Pass the filter to the context
        return context

class InvoiceUpdateView(UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "invoices/update_invoice.html"
    success_url = reverse_lazy("list_invoices")

    def get_context_data(self, **kwargs):
        # Get the existing context
        context = super().get_context_data(**kwargs)

        # Add the line items related to this invoice
        context['line_items'] = self.object.line_items.all()

        return context
