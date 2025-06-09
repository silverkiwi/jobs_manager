"""
Client REST URLs

URLs para as views REST do módulo Client seguindo padrões RESTful:
- Endpoints claramente definidos
- Verbos HTTP apropriados
- Estrutura consistente com outros módulos REST
"""

from django.urls import path
from apps.client.views.client_rest_views import (
    ClientSearchRestView,
    ClientContactsRestView,
)

app_name = "clients_rest"

urlpatterns = [
    # Client search REST endpoint
    path(
        "search/",
        ClientSearchRestView.as_view(),
        name="client_search_rest",
    ),
    
    # Client contacts REST endpoint
    path(
        "<uuid:client_id>/contacts/",
        ClientContactsRestView.as_view(),
        name="client_contacts_rest",
    ),
]
