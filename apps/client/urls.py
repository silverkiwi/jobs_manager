"""
URL Configuration for Client App

This module contains all URL patterns related to client management:
- Client CRUD operations
- Client contact information
- Client search and listing
- Unused clients management
- etc.
"""

from django.urls import path

import apps.client.views as client_view

app_name = "clients"

urlpatterns = [
    # Client API endpoints
    path(
        "api/<uuid:client_id>/contact-persons/",
        client_view.get_client_contact_persons,
        name="api_get_client_contact_persons",
    ),
    path(
        "api/<uuid:client_id>/phones/",
        client_view.get_client_phones,
        name="api_get_client_phones",
    ),
    path("api/all/", client_view.get_all_clients_api, name="api_clients_all"),
    path(
        "api/search/",
        client_view.ClientSearch,
        name="client_search_api",
    ),
    path("api/detail/", client_view.client_detail, name="client_detail"),
    
    # ClientContact API endpoints
    path(
        "api/client/<uuid:client_id>/contacts/",
        client_view.get_client_contacts_api,
        name="api_get_client_contacts",
    ),
    path(
        "api/client/contact/",
        client_view.create_client_contact_api,
        name="api_create_client_contact",
    ),
    path(
        "api/client/contact/<uuid:contact_id>/",
        client_view.client_contact_detail_api,
        name="api_client_contact_detail",
    ),
    # Client view endpoints
    path("", client_view.ClientListView.as_view(), name="list_clients"),
    path(
        "<uuid:pk>/",
        client_view.ClientUpdateView.as_view(),
        name="update_client",
    ),
    path("add/", client_view.AddClient, name="add_client"),
    path(
        "xero/unused/",
        client_view.UnusedClientsView.as_view(),
        name="xero_unused_clients",
    ),
]
