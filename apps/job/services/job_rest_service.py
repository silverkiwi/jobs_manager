"""
Job REST Service Layer

Seguindo os princípios do SRP (Single Responsibility Principle) e guidelines de código limpo.
Toda lógica de negócio para operações REST de Jobs deve ser implementada aqui.
"""

import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.job.models import Job, JobPricing, JobEvent
from apps.job.enums import JobPricingMethodology, JobPricingStage
from apps.job.serializers import JobSerializer, JobPricingSerializer
from apps.client.models import Client, ClientContact
from apps.accounts.models import Staff
from apps.job.services.job_service import get_job_with_pricings

logger = logging.getLogger(__name__)


class JobRestService:
    """
    Service layer para operações REST de Jobs.
    Implementa todas as regras de negócio relacionadas à manipulação de Jobs via API REST.
    """

    @staticmethod
    def create_job(data: Dict[str, Any], user: Staff) -> Job:
        """
        Cria um novo Job com dados essenciais.
        Aplica early return para validações.
        
        Args:
            data: Dados do formulário de criação
            user: Usuário que está criando o job
            
        Returns:
            Job: Instância do job criado
            
        Raises:
            ValueError: Se dados obrigatórios estão faltando
        """
        # Guard clauses - early return para validações
        if not data.get('name'):
            raise ValueError("Nome do Job é obrigatório")
            
        if not data.get('client_id'):
            raise ValueError("Cliente é obrigatório")
        
        try:
            client = Client.objects.get(id=data['client_id'])
        except Client.DoesNotExist:
            raise ValueError("Cliente não encontrado")
        
        # Switch-case seria ideal aqui, mas Python não tem antes do 3.10
        # Usando match-case para lógica de decisão clara
        job_data = {
            'name': data['name'],
            'client': client,
            'created_by': user,
        }
        
        # Campos opcionais - apenas se fornecidos
        optional_fields = ['description', 'order_number', 'notes', 'contact_person']
        for field in optional_fields:
            if data.get(field):
                job_data[field] = data[field]
        
        # Contato (relacionamento opcional)
        if data.get('contact_id'):
            try:
                contact = ClientContact.objects.get(id=data['contact_id'])
                job_data['contact'] = contact
            except ClientContact.DoesNotExist:
                logger.warning(f"Contato {data['contact_id']} não encontrado, ignorando")
        
        with transaction.atomic():
            job = Job(**job_data)
            job.save(staff=user)
            
            # Log da criação
            JobEvent.objects.create(
                job=job,
                staff=user,
                event_type='job_created',
                description=f'Job "{job.name}" criado'
            )
            
            logger.info(f"Job {job.id} criado com sucesso por {user.username}")
            
        return job

    @staticmethod
    def get_job_for_edit(job_id: UUID) -> Dict[str, Any]:
        """
        Busca dados completos de um Job para edição.
        
        Args:
            job_id: UUID do job
            
        Returns:
            Dict com dados do job e pricing
        """
        job = get_job_with_pricings(job_id)
        
        # Serializar dados principais
        job_data = JobSerializer(job).data
        
        # Buscar pricings mais recentes
        latest_pricings = {
            'estimate': job.latest_estimate_pricing,
            'quote': job.latest_quote_pricing,
            'reality': job.latest_reality_pricing,
        }
        
        # Serializar pricings
        latest_pricings_data = {}
        for stage, pricing in latest_pricings.items():
            if pricing:
                latest_pricings_data[f'{stage}_pricing'] = JobPricingSerializer(pricing).data
        
        # Buscar eventos do job
        events = JobEvent.objects.filter(job=job).order_by('-timestamp')[:10]
        events_data = [
            {
                'id': str(event.id),
                'timestamp': event.timestamp.isoformat(),
                'event_type': event.event_type,
                'description': event.description,
                'staff': event.staff.get_display_full_name() if event.staff else 'Sistema'
            }
            for event in events
        ]
        
        return {
            'job': job_data,
            'latest_pricings': latest_pricings_data,
            'events': events_data,
            'company_defaults': JobRestService._get_company_defaults(),
        }

    @staticmethod
    def update_job(job_id: UUID, data: Dict[str, Any], user: Staff) -> Job:
        """
        Atualiza um Job existente.
        
        Args:
            job_id: UUID do job
            data: Dados para atualização
            user: Usuário que está atualizando
            
        Returns:
            Job: Instância atualizada
        """
        job = get_object_or_404(Job, id=job_id)
        
        # Usar serializer para validação e atualização
        serializer = JobSerializer(
            instance=job, 
            data=data, 
            partial=True, 
            context={'request': type('MockRequest', (), {'user': user})()}
        )
        
        if not serializer.is_valid():
            raise ValueError(f"Dados inválidos: {serializer.errors}")
        
        with transaction.atomic():
            job = serializer.save(staff=user)
            
            # Log da atualização
            JobEvent.objects.create(
                job=job,
                staff=user,
                event_type='job_updated',
                description='Job atualizado via interface REST'
            )
        
        return job

    @staticmethod
    def toggle_complex_job(job_id: UUID, complex_job: bool, user: Staff) -> Dict[str, Any]:
        """
        Alterna o modo complex_job de um Job.
        Implementa regras de validação específicas.
        
        Args:
            job_id: UUID do job
            complex_job: Novo valor booleano
            user: Usuário fazendo a alteração
            
        Returns:
            Dict com resultado da operação
        """
        # Early return - validação de tipos
        if not isinstance(complex_job, bool):
            raise ValueError("complex_job deve ser um valor booleano")
        
        job = get_object_or_404(Job, id=job_id)
        
        # Guard clause - verificar se pode desabilitar modo complexo
        if not complex_job and job.complex_job:
            validation_result = JobRestService._validate_can_disable_complex_mode(job)
            if not validation_result['can_disable']:
                raise ValueError(validation_result['reason'])
        
        with transaction.atomic():
            job.complex_job = complex_job
            job.save()
            
            # Log da alteração
            mode = "ativado" if complex_job else "desativado"
            JobEvent.objects.create(
                job=job,
                staff=user,
                event_type='complex_mode_changed',
                description=f'Modo itemizado {mode}'
            )
        
        return {
            'success': True,
            'job_id': str(job_id),
            'complex_job': complex_job,
            'message': 'Job atualizado com sucesso'
        }

    @staticmethod
    def toggle_pricing_methodology(job_id: UUID, methodology: str, user: Staff) -> Dict[str, Any]:
        """
        Alterna a metodologia de pricing do Job.
        
        Args:
            job_id: UUID do job
            methodology: Nova metodologia
            user: Usuário fazendo a alteração
            
        Returns:
            Dict com resultado da operação
        """
        # Guard clause - validação de valores permitidos
        valid_methodologies = [choice[0] for choice in JobPricingMethodology.choices]
        if methodology not in valid_methodologies:
            raise ValueError(f"Metodologia inválida. Opções: {valid_methodologies}")
        
        job = get_object_or_404(Job, id=job_id)
        
        # Switch-case usando match (Python 3.10+) para decisão de fluxo
        match methodology:
            case JobPricingMethodology.TIME_AND_MATERIALS:
                new_methodology = JobPricingMethodology.TIME_AND_MATERIALS
            case JobPricingMethodology.FIXED_PRICE:
                new_methodology = JobPricingMethodology.FIXED_PRICE
            case _:
                raise ValueError("Metodologia de pricing não reconhecida")
        
        with transaction.atomic():
            job.pricing_methodology = new_methodology
            job.save()
            
            # Log da alteração
            JobEvent.objects.create(
                job=job,
                staff=user,
                event_type='pricing_methodology_changed',
                description=f'Metodologia alterada para {new_methodology}'
            )
        
        return {
            'success': True,
            'job_id': str(job_id),
            'pricing_methodology': new_methodology,
            'message': 'Metodologia de pricing atualizada com sucesso'
        }

    @staticmethod
    def add_job_event(job_id: UUID, description: str, user: Staff) -> Dict[str, Any]:
        """
        Adiciona um evento manual ao Job.
        
        Args:
            job_id: UUID do job
            description: Descrição do evento
            user: Usuário criando o evento
            
        Returns:
            Dict com dados do evento criado
        """
        # Guard clause - validação de entrada
        if not description or not description.strip():
            raise ValueError("Descrição do evento é obrigatória")
        
        job = get_object_or_404(Job, id=job_id)
        
        event = JobEvent.objects.create(
            job=job,
            staff=user,
            description=description.strip(),
            event_type='manual_note'
        )
        
        logger.info(f"Evento {event.id} criado para job {job_id} por {user.username}")
        
        return {
            'success': True,
            'event': {
                'id': str(event.id),
                'timestamp': event.timestamp.isoformat(),
                'event_type': event.event_type,
                'description': event.description,
                'staff': user.get_display_full_name() if user else 'Sistema'
            }
        }

    @staticmethod
    def delete_job(job_id: UUID, user: Staff) -> Dict[str, Any]:
        """
        Deleta um Job se permitido pelas regras de negócio.
        
        Args:
            job_id: UUID do job
            user: Usuário tentando deletar
            
        Returns:
            Dict com resultado da operação
        """
        job = get_object_or_404(Job, id=job_id)
        
        # Guard clause - verificar se pode deletar
        reality_pricing = job.pricings.filter(
            pricing_stage=JobPricingStage.REALITY,
            is_historical=False
        ).first()
        
        if reality_pricing and (reality_pricing.total_revenue > 0 or reality_pricing.total_cost > 0):
            raise ValueError(
                "Não é possível deletar este job porque ele possui custos ou receitas reais."
            )
        
        job_name = job.name
        job_number = job.job_number
        
        with transaction.atomic():
            job.delete()
            
            logger.info(
                f"Job {job_number} '{job_name}' deletado por {user.username}"
            )
        
        return {
            'success': True,
            'message': f'Job {job_number} deletado com sucesso'
        }

    @staticmethod
    def _validate_can_disable_complex_mode(job: Job) -> Dict[str, Any]:
        """
        Valida se o job pode ter o modo complexo desabilitado.
        
        Args:
            job: Instância do Job
            
        Returns:
            Dict com resultado da validação
        """
        for pricing in job.pricings.all():
            if not pricing:
                continue
                
            # Verificar se há múltiplas entradas
            if (pricing.time_entries.count() > 1 or 
                pricing.material_entries.count() > 1 or 
                pricing.adjustment_entries.count() > 1):
                return {
                    'can_disable': False,
                    'reason': 'Não é possível desabilitar modo complexo com múltiplas entradas de pricing'
                }
        
        return {'can_disable': True, 'reason': ''}

    @staticmethod
    def _get_company_defaults() -> Dict[str, Any]:
        """
        Busca configurações padrão da empresa.
        
        Returns:
            Dict com configurações padrão
        """
        from apps.job.helpers import get_company_defaults
        
        defaults = get_company_defaults()
        return {
            'materials_markup': float(defaults.materials_markup),
            'time_markup': float(defaults.time_markup),
            'charge_out_rate': float(defaults.charge_out_rate),
            'wage_rate': float(defaults.wage_rate),
        }
