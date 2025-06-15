"""
URL Configuration for Client App

This module contains all URL patterns related to client management:
- Client CRUD operations
- Client contact information
- Client search and listing
- Unused clients management
- etc.
"""

from django.urls import path, include

import apps.client.views as client_view

app_name = "clients"

urlpatterns = [
    # REST API endpoints
    path("rest/", include("apps.client.urls_rest")),
    
]
