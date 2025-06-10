"""
Job REST Views

REST views for the Job module following clean code principles:
- SRP (Single Responsibility Principle)
- Early return and guard clauses
- Delegation to service layer
- Views as orchestrators only
"""

import logging
import json
from typing import Dict, Any

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.job.services.job_rest_service import JobRestService
from apps.job.helpers import DecimalEncoder

logger = logging.getLogger(__name__)


class BaseJobRestView(APIView):
    """
    Base view for Job REST operations.
    Implements common functionality like JSON parsing and error handling.
    Inherits from APIView for JWT authentication support.
    """    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """Remove manual authentication check - let DRF handle it."""
        return super().dispatch(request, *args, **kwargs)
    
    def parse_json_body(self, request) -> Dict[str, Any]:
        """
        Parse the JSON body of the request.
        Apply early return in case of error.
        """
        if not request.body:
            raise ValueError("Request body is empty")
        
        try:
            return json.loads(request.body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}")
    def handle_service_error(self, error: Exception) -> Response:
        """
        Centralise service layer error handling.
        """
        error_message = str(error)
        
        # Switch-case for different error types
        match type(error).__name__:
            case 'ValueError':
                return Response({'error': error_message}, status=status.HTTP_400_BAD_REQUEST)
            case 'PermissionError':
                return Response({'error': error_message}, status=status.HTTP_403_FORBIDDEN)
            case 'NotFound' | 'Http404':
                return Response({'error': 'Resource not found'}, status=status.HTTP_404_NOT_FOUND)
            case _:
                logger.exception(f"Unhandled error: {error}")
                return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class JobCreateRestView(BaseJobRestView):
    """
    REST view for Job creation.
    Single responsibility: orchestrate job creation.
    """
    
    def post(self, request):
        """
        Create a new Job.
        
        Expected JSON:
        {
            "name": "Job Name",
            "client_id": "client-uuid",
            "description": "Optional description",
            "order_number": "Optional order number",
            "notes": "Optional notes",
            "contact_id": "optional-contact-uuid"
        }
        """
        try:
            data = self.parse_json_body(request)
            job = JobRestService.create_job(data, request.user)
            return Response({
                'success': True,
                'job_id': str(job.id),
                'job_number': job.job_number,
                'message': 'Job created successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name='dispatch')
class JobDetailRestView(BaseJobRestView):
    """
    REST view for CRUD operations on a specific Job.
    """
    def get(self, request, job_id):
        """
        Fetch complete Job data for editing.
        """
        try:
            job_data = JobRestService.get_job_for_edit(job_id)
            return Response({
                'success': True,
                'data': job_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return self.handle_service_error(e)
    
    def put(self, request, job_id):
        """
        Update Job data (autosave).
        """
        try:
            data = self.parse_json_body(request)
            job = JobRestService.update_job(job_id, data, request.user)
            
            # Get updated job data to return
            job_data = JobRestService.get_job_for_edit(job_id)
            
            return Response({
                'success': True,
                'data': job_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return self.handle_service_error(e)
    def delete(self, request, job_id):
        """
        Delete a Job if permitted.
        """        
        try:
            result = JobRestService.delete_job(job_id, request.user)
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            return self.handle_service_error(e)


@method_decorator(csrf_exempt, name='dispatch')
class JobToggleComplexRestView(BaseJobRestView):
    """
    REST view for toggling Job complex mode.
    """
    def post(self, request):
        """
        Toggle the complex_job mode.
        
        Expected JSON:
        {
            "job_id": "job-uuid",
            "complex_job": true/false
        }
        """
        try:
            data = self.parse_json_body(request)
            
            # Guard clauses - validate required data
            if 'job_id' not in data:
                raise ValueError("job_id is required")
            
            if 'complex_job' not in data:
                raise ValueError("complex_job is required")
            
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
    REST view for toggling pricing methodology.
    """
    
    def post(self, request):
        """
        Toggle the pricing methodology.
          Expected JSON:
        {
            "job_id": "job-uuid",
            "pricing_methodology": "time_materials" | "fixed_price"
        }
        """
        try:
            data = self.parse_json_body(request)
            
            # Guard clauses
            if 'job_id' not in data:
                raise ValueError("job_id is required")
            
            if 'pricing_methodology' not in data:
                raise ValueError("pricing_methodology is required")
            
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
    REST view for Job events.
    """
    
    def post(self, request, job_id):
        """
        Add a manual event to the Job.
        
        Expected JSON:
        {
            "description": "Event description"
        }
        """
        try:
            data = self.parse_json_body(request)
            
            # Guard clause
            if 'description' not in data:
                raise ValueError("description is required")
            
            result = JobRestService.add_job_event(
                job_id,
                data['description'],
                request.user
            )
            
            return JsonResponse(result, status=201)
            
        except Exception as e:
            return self.handle_service_error(e)


# Functional views for compatibility with existing URLs
@require_http_methods(["POST"])
@csrf_exempt
def create_job_rest_api(request):
    """
    Functional view for Job creation (compatibility).
    Delegates to the class-based view.
    """
    view = JobCreateRestView.as_view()
    return view(request)


@require_http_methods(["GET", "PUT", "DELETE"])
@csrf_exempt
def job_detail_rest_api(request, job_id):
    """
    Functional view for specific Job operations (compatibility).
    """
    view = JobDetailRestView.as_view()
    return view(request, job_id=job_id)


@require_http_methods(["POST"])
@csrf_exempt
def toggle_complex_job_rest_api(request):
    """
    Functional view for complex job toggle (compatibility).
    """
    view = JobToggleComplexRestView.as_view()
    return view(request)


@require_http_methods(["POST"])
@csrf_exempt
def toggle_pricing_methodology_rest_api(request):
    """
    Functional view for pricing methodology toggle (compatibility).
    """
    view = JobTogglePricingMethodologyRestView.as_view()
    return view(request)


@require_http_methods(["POST"])
@csrf_exempt
def add_job_event_rest_api(request, job_id):
    """
    Functional view for adding event (compatibility).
    """
    view = JobEventRestView.as_view()
    return view(request, job_id=job_id)
