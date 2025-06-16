"""
Quote Import REST Views

REST endpoints for importing quotes from spreadsheets.
Follows clean code principles:
- Views as orchestrators only
- Delegation to service layer
- Proper error handling and response formatting
"""

import logging
from typing import Dict, Any
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from apps.job.models import Job
from apps.job.services.import_quote_service import (
    import_quote_from_file,
    preview_quote_import,
    QuoteImportError,
    QuoteImportResult
)
from apps.job.serializers.costing_serializer import CostSetSerializer

logger = logging.getLogger(__name__)


class QuoteImportPreviewView(APIView):
    """
    Preview quote import changes without actually importing.
    
    POST /jobs/<job_id>/quote/import/preview/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, job_id):
        """Preview quote import from uploaded file"""
        # Early return: validate job exists
        job = get_object_or_404(Job, pk=job_id)
        
        # Early return: validate file upload
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_file = request.FILES['file']
        
        # Early return: validate file type
        if not uploaded_file.name.endswith(('.xlsx', '.xls')):            return Response(
                {'error': 'Only Excel files (.xlsx, .xls) are supported'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Save uploaded file temporarily
            import tempfile
            import os
            
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"quote_preview_{uploaded_file.name}")
            
            with open(temp_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Preview the import
            preview_data = preview_quote_import(job, temp_path)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Format response
            response_data = {
                'job_id': str(job.id),
                'job_name': job.name,
                'preview': preview_data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error previewing quote import for job {job_id}: {str(e)}")
            return Response(
                {'error': f'Preview failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QuoteImportView(APIView):
    """
    Import quote from spreadsheet file.
    
    POST /jobs/<job_id>/quote/import/
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, job_id):
        """Import quote from uploaded file"""
        # Early return: validate job exists
        job = get_object_or_404(Job, pk=job_id)
        
        # Early return: validate file upload
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        uploaded_file = request.FILES['file']
        
        # Early return: validate file type
        if not uploaded_file.name.endswith(('.xlsx', '.xls')):
            return Response(
                {'error': 'Only Excel files (.xlsx, .xls) are supported'},
                status=status.HTTP_400_BAD_REQUEST
            )
          # Get options from request
        skip_validation = request.data.get('skip_validation', 'false').lower() == 'true'
        
        try:
            # Save uploaded file temporarily
            import tempfile
            import os
            
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"quote_import_{uploaded_file.name}")
            
            with open(temp_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Import the quote
            result = import_quote_from_file(job, temp_path, skip_validation=skip_validation)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Format response based on result
            if result.success:
                response_data = {
                    'success': True,
                    'message': 'Quote imported successfully',
                    'job_id': str(job.id),
                    'cost_set': CostSetSerializer(result.cost_set).data if result.cost_set else None,
                    'changes': {
                        'additions': len(result.diff_result.to_add) if result.diff_result else 0,
                        'updates': len(result.diff_result.to_update) if result.diff_result else 0,
                        'deletions': len(result.diff_result.to_delete) if result.diff_result else 0
                    }
                }
                
                # Add validation report if available
                if result.validation_report:
                    response_data['validation'] = {
                        'warnings_count': len(result.validation_report.warnings),
                        'has_warnings': len(result.validation_report.warnings) > 0
                    }
                
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                # Import failed
                response_data = {
                    'success': False,
                    'error': result.error_message,
                    'job_id': str(job.id)
                }
                
                # Add validation details if available
                if result.validation_report:
                    response_data['validation'] = {
                        'errors_count': len(result.validation_report.errors),
                        'critical_count': len(result.validation_report.critical_issues),
                        'can_proceed': result.validation_report.can_proceed
                    }
                
                return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
                
        except QuoteImportError as e:
            logger.error(f"Quote import error for job {job_id}: {str(e)}")
            return Response(
                {'error': str(e), 'job_id': str(job.id)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error importing quote for job {job_id}: {str(e)}")
            return Response(
                {'error': f'Import failed: {str(e)}', 'job_id': str(job.id)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QuoteImportStatusView(APIView):
    """
    Get current quote import status and latest quote information.
    
    GET /jobs/<job_id>/quote/status/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, job_id):
        """Get quote status for job"""
        # Early return: validate job exists
        job = get_object_or_404(Job, pk=job_id)
        
        try:
            # Get latest quote
            latest_quote = job.get_latest('quote')
            
            response_data = {
                'job_id': str(job.id),
                'job_name': job.name,
                'has_quote': latest_quote is not None
            }
            
            if latest_quote:
                response_data.update({
                    'quote': CostSetSerializer(latest_quote).data,
                    'revision': latest_quote.rev,
                    'created': latest_quote.created,
                    'summary': latest_quote.summary
                })
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting quote status for job {job_id}: {str(e)}")
            return Response(
                {'error': f'Failed to get quote status: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
