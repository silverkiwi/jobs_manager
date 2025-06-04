"""
Stock Management views for the purchasing app.
Handles stock listing, creation, consumption and search operations.
"""

import json
import logging
from django.views.generic import ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.db import transaction

from apps.workflow.models.stock import Stock
from apps.workflow.utils import get_active_jobs

logger = logging.getLogger(__name__)


class UseStockView(LoginRequiredMixin, TemplateView):
    """View for using stock items on jobs."""
    
    template_name = 'purchasing/use_stock.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if job_id is provided in query string
        job_id = self.kwargs.get('job_id') or self.request.GET.get('job_id')
        
        # Get all active stock items
        stock_items = Stock.objects.filter(is_active=True).order_by('description')
        
        # Get the stock holding job and active jobs
        from apps.workflow.models.company_defaults import CompanyDefaults
        stock_holding_job = Stock.get_stock_holding_job()
        active_jobs = get_active_jobs().exclude(id=stock_holding_job.id).order_by('job_number')
        
        # Get company defaults for markup calculation
        company_defaults = CompanyDefaults.get_instance()
        materials_markup = company_defaults.materials_markup
        
        # Prepare stock data for AG Grid
        stock_data = []
        for item in stock_items:
            # Implementation for stock data preparation
            pass
        
        # If job_id is provided, get the job object to pass to the template
        default_job = None
        if job_id:
            # Implementation for default job
            pass
        
        context.update({
            'title': 'Use Stock',
            'stock_items': stock_items,
            'stock_data_json': json.dumps(stock_data),
            'active_jobs': active_jobs,
            'stock_holding_job': stock_holding_job,
            'default_job_id': str(job_id) if job_id else None,
        })
        
        return context


# Stock API Views
@require_http_methods(["POST"])
@transaction.atomic
def consume_stock_api_view(request):
    """
    API endpoint to record stock consumption for a job and create a MaterialEntry.
    """
    try:
        # Implementation for stock consumption
        pass
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Http404 as e:         
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        logger.error(f"Error in consume_stock_api_view: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
@transaction.atomic
def create_stock_api_view(request):
    """
    API endpoint to create a new stock item.
    """
    try:
        # Implementation for stock creation
        pass
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        logger.error(f"Error in create_stock_api_view: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["GET"])
def search_available_stock_api(request):
    """
    API endpoint to search available stock items for autocomplete.
    Searches active stock items matching the search term.
    """
    search_term = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 25))

    results = []

    if search_term:
        # Implementation for stock search
        pass

    return JsonResponse({'results': results})


@require_http_methods(["POST"])
@transaction.atomic
def deactivate_stock_api_view(request, stock_id):
    """
    API endpoint to deactivate a stock item (soft delete).
    Sets is_active=False to hide it from the UI.
    """
    try:
        # Implementation for stock deactivation
        pass
    except Exception as e:
        logger.error(f"Error in deactivate_stock_api_view: {e}")
        return JsonResponse({'success': False, 'error': str(e)})
