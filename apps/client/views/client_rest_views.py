"""
Client REST Views

Views REST para o módulo Client seguindo princípios de clean code:
- SRP (Single Responsibility Principle) 
- Early return e guard clauses
- Delegação para service layer
- Views como orquestradoras apenas
"""

import logging
from typing import Dict, Any

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Q

from apps.client.models import Client

logger = logging.getLogger(__name__)


class BaseClientRestView(View):
    """
    View base para operações REST de Clients.
    Implementa funcionalidades comuns como parsing de JSON e tratamento de erros.
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def handle_error(self, error: Exception, message: str = "Internal server error") -> JsonResponse:
        """
        Centraliza tratamento de erros seguindo princípios de clean code.
        """
        logger.error(f"{message}: {str(error)}")
        return JsonResponse(
            {'error': message, 'details': str(error)}, 
            status=500
        )


class ClientSearchRestView(BaseClientRestView):
    """
    View REST para busca de clientes.
    Implementa funcionalidade de busca por nome com paginação.
    """
    
    def get(self, request) -> JsonResponse:
        """
        Busca clientes por nome seguindo early return pattern.
        """
        try:
            # Guard clause: validação de query parameter
            query = request.GET.get("q", "").strip()
            if not query:
                return JsonResponse({"results": []})
            
            # Guard clause: query muito curta
            if len(query) < 3:
                return JsonResponse({"results": []})
            
            # Busca clientes seguindo princípios de clean code
            clients = self._search_clients(query)
            results = self._format_client_results(clients)
            
            return JsonResponse({"results": results})
            
        except Exception as e:
            return self.handle_error(e, "Error searching clients")
    
    def _search_clients(self, query: str):
        """
        Executa busca de clientes com filtros apropriados.
        SRP: responsabilidade única de buscar clientes.
        """
        return Client.objects.filter(
            Q(name__icontains=query)
        ).order_by('name')[:10]
    
    def _format_client_results(self, clients) -> list:
        """
        Formata resultados da busca seguindo SRP.
        """
        return [
            {
                "id": str(client.id),
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


class ClientContactsRestView(BaseClientRestView):
    """
    View REST para busca de contatos de um cliente.
    """
    def get(self, request, client_id: str) -> JsonResponse:
        """
        Busca contatos de um cliente específico.
        """
        try:
            # Guard clause: validação de client_id
            if not client_id:
                return JsonResponse({"error": "Client ID is required"}, status=400)
            
            # Busca cliente seguindo early return
            try:
                client = Client.objects.get(id=client_id)
            except Client.DoesNotExist:
                return JsonResponse({"error": "Client not found"}, status=404)
            
            # Busca contatos do cliente
            contacts = self._get_client_contacts(client)
            results = self._format_contact_results(contacts)
            
            return JsonResponse({"results": results})
            
        except Exception as e:
            return self.handle_error(e, "Error fetching client contacts")
    
    def _get_client_contacts(self, client):
        """
        Busca contatos do cliente seguindo SRP.
        """
        return client.contacts.all().order_by('name')
    
    def _format_contact_results(self, contacts) -> list:
        """
        Formata resultados dos contatos seguindo SRP.
        """
        return [
            {
                "id": str(contact.id),
                "name": contact.name,
                "email": contact.email or "",
                "phone": contact.phone or "",
                "position": contact.position or "",
                "is_primary": contact.is_primary,
            }
            for contact in contacts
        ]
