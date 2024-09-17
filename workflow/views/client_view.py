import django_filters
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django_filters.views import FilterView
from workflow.models import Client

class ClientFilter(django_filters.FilterSet):
    class Meta:
        model = Client
        fields = {
            'name': ['icontains'],  # Search by name (case-insensitive)
            'email': ['icontains'],  # Search by email (case-insensitive)
            'is_account_customer': ['exact'],  # Filter by whether they are account customers
        }

class ClientListView(FilterView):
    model = Client
    template_name = "workflow/list_clients.html"
    filterset_class = ClientFilter
    context_object_name = 'clients'
    paginate_by = 20  # To handle large datasets, use pagination

class ClientUpdateView(UpdateView):
    model = Client
    template_name = "workflow/update_client.html"
    fields = ['name', 'email', 'phone']  # Adjust fields as needed
    success_url = reverse_lazy('list_clients')  # Redirect after successful edit
