"""
Job REST Views

Views REST para o módulo Job seguindo princípios de clean code:
- SRP (Single Responsibility Principle)
- Early return e guard clauses
- Delegação para service layer
- Views como orquestradoras apenas
"""

import logging
import json
from typing import Dict, Any

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction

from apps.job.services.job_rest_service import JobRestService
from apps.job.helpers import DecimalEncoder

logger = logging.getLogger(__name__)


class BaseJobRestView(View):
    """
    View base para operações REST de Jobs.
    Implementa funcionalidades comuns como parsing de JSON e tratamento de erros.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Garante que o usuário está autenticado."""
        # Guard clause - verificação de autenticação
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Autenticação necessária'}, status=401)
        
        return super().dispatch(request, *args, **kwargs)
    
    def parse_json_body(self, request) -> Dict[str, Any]:
        """
        Faz parse do corpo JSON da requisição.
        Aplica early return em caso de erro.
        """
        if not request.body:
            raise ValueError("Corpo da requisição está vazio")
        
        try:
            return json.loads(request.body)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON inválido: {str(e)}")
    
    def handle_service_error(self, error: Exception) -> JsonResponse:
        """
        Centraliza tratamento de erros do service layer.
        """
        error_message = str(error)
        
        # Switch-case para diferentes tipos de erro
        match type(error).__name__:
            case 'ValueError':
                return JsonResponse({'error': error_message}, status=400)
            case 'PermissionError':
                return JsonResponse({'error': error_message}, status=403)
            case 'NotFound' | 'Http404':
                return JsonResponse({'error': 'Recurso não encontrado'}, status=404)
            case _:
                logger.exception(f"Erro não tratado: {error}")
                return JsonResponse({'error': 'Erro interno do servidor'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class JobCreateRestView(BaseJobRestView):
    """
    View REST para criação de Jobs.
    Responsabilidade única: orquestrar criação de jobs.
    """
    
    def post(self, request):
        """
        Cria um novo Job.
        
        Expected JSON:
        {
            "name": "Nome do Job",
            "client_id": "uuid-do-cliente",
            "description": "Descrição opcional",
            "order_number": "Número do pedido opcional",
            "notes": "Notas opcionais",
            "contact_id": "uuid-do-contato-opcional"
        }
        """
        try:
            data = self.parse_json_body(request)
            job = JobRestService.create_job(data, request.user)
            
            return JsonResponse({
                'success': True,
                'job_id': str(job.id),
                'job_number': job.job_number,
                'message': 'Job criado com sucesso'
            }, status=201)
            
        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name='dispatch')
class JobDetailRestView(BaseJobRestView):
    """
    View REST para operações CRUD de um Job específico.
    """
    
    def get(self, request, job_id):
        """
        Busca dados completos de um Job para edição.
        """
        try:
            job_data = JobRestService.get_job_for_edit(job_id)
            
            return JsonResponse({
                'success': True,
                'data': job_data
            }, cls=DecimalEncoder)
            
        except Exception as e:
            return self.handle_service_error(e)
    
    def put(self, request, job_id):
        """
        Atualiza dados de um Job (autosave).
        """
        try:
            data = self.parse_json_body(request)
            job = JobRestService.update_job(job_id, data, request.user)
            
            return JsonResponse({
                'success': True,
                'job_id': str(job.id),
                'message': 'Job atualizado com sucesso'
            })
            
        except Exception as e:
            return self.handle_service_error(e)
    
    def delete(self, request, job_id):
        """
        Deleta um Job se permitido.
        """
        try:
            result = JobRestService.delete_job(job_id, request.user)
            return JsonResponse(result)
            
        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name='dispatch')
class JobToggleComplexRestView(BaseJobRestView):
    """
    View REST para alternar modo complexo do Job.
    """
    
    def post(self, request):
        """
        Alterna o modo complex_job.
        
        Expected JSON:
        {
            "job_id": "uuid-do-job",
            "complex_job": true/false
        }
        """
        try:
            data = self.parse_json_body(request)
            
            # Guard clauses - validação de dados obrigatórios
            if 'job_id' not in data:
                raise ValueError("job_id é obrigatório")
            
            if 'complex_job' not in data:
                raise ValueError("complex_job é obrigatório")
            
            result = JobRestService.toggle_complex_job(
                data['job_id'], 
                data['complex_job'], 
                request.user
            )
            
            return JsonResponse(result)
            
        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name='dispatch')
class JobTogglePricingMethodologyRestView(BaseJobRestView):
    """
    View REST para alternar metodologia de pricing.
    """
    
    def post(self, request):
        """
        Alterna a metodologia de pricing.
        
        Expected JSON:
        {
            "job_id": "uuid-do-job",
            "pricing_methodology": "time_materials" | "fixed_price"
        }
        """
        try:
            data = self.parse_json_body(request)
            
            # Guard clauses
            if 'job_id' not in data:
                raise ValueError("job_id é obrigatório")
            
            if 'pricing_methodology' not in data:
                raise ValueError("pricing_methodology é obrigatório")
            
            result = JobRestService.toggle_pricing_methodology(
                data['job_id'],
                data['pricing_methodology'],
                request.user
            )
            
            return JsonResponse(result)
            
        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name='dispatch')
class JobEventRestView(BaseJobRestView):
    """
    View REST para eventos de Job.
    """
    
    def post(self, request, job_id):
        """
        Adiciona um evento manual ao Job.
        
        Expected JSON:
        {
            "description": "Descrição do evento"
        }
        """
        try:
            data = self.parse_json_body(request)
            
            # Guard clause
            if 'description' not in data:
                raise ValueError("description é obrigatória")
            
            result = JobRestService.add_job_event(
                job_id,
                data['description'],
                request.user
            )
            
            return JsonResponse(result, status=201)
            
        except Exception as e:
            return self.handle_service_error(e)


# Views funcionais para compatibilidade com URLs existentes
@require_http_methods(["POST"])
@csrf_exempt
def create_job_rest_api(request):
    """
    View funcional para criação de Job (compatibilidade).
    Delega para a view baseada em classe.
    """
    view = JobCreateRestView.as_view()
    return view(request)


@require_http_methods(["GET", "PUT", "DELETE"])
@csrf_exempt
def job_detail_rest_api(request, job_id):
    """
    View funcional para operações em Job específico (compatibilidade).
    """
    view = JobDetailRestView.as_view()
    return view(request, job_id=job_id)


@require_http_methods(["POST"])
@csrf_exempt
def toggle_complex_job_rest_api(request):
    """
    View funcional para toggle de complex job (compatibilidade).
    """
    view = JobToggleComplexRestView.as_view()
    return view(request)


@require_http_methods(["POST"])
@csrf_exempt
def toggle_pricing_methodology_rest_api(request):
    """
    View funcional para toggle de pricing methodology (compatibilidade).
    """
    view = JobTogglePricingMethodologyRestView.as_view()
    return view(request)


@require_http_methods(["POST"])
@csrf_exempt
def add_job_event_rest_api(request, job_id):
    """
    View funcional para adicionar evento (compatibilidade).
    """
    view = JobEventRestView.as_view()
    return view(request, job_id=job_id)
