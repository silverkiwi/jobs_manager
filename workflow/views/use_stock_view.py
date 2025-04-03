import json
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from workflow.models import Stock, CompanyDefaults
from workflow.utils import get_active_jobs

logger = logging.getLogger(__name__)

@login_required
def use_stock_view(request):
    """
    View for the Use Stock page.
    Displays a list of available stock items and allows searching and consuming stock.
    """
    # Get all active stock items
    stock_items = Stock.objects.filter(is_active=True).order_by('description')
    
    # Get the stock holding job and active jobs
    stock_holding_job = Stock.get_stock_holding_job()
    active_jobs = get_active_jobs().exclude(id=stock_holding_job.id).order_by('job_number')
    
    # Get company defaults for markup calculation
    company_defaults = CompanyDefaults.get_instance()
    materials_markup = company_defaults.materials_markup
    
    # Prepare stock data for AG Grid
    stock_data = []
    for item in stock_items:
        # Calculate unit revenue using the materials markup
        unit_revenue = item.unit_cost * (1 + materials_markup)
        total_value = item.quantity * item.unit_cost
        
        stock_data.append({
            'id': item.id,
            'description': item.description,
            'quantity': float(item.quantity),
            'unit_cost': float(item.unit_cost),
            'unit_revenue': float(unit_revenue),
            'total_value': float(total_value)
        })
    
    context = {
        'title': 'Use Stock',
        'stock_items': stock_items,
        'stock_data_json': json.dumps(stock_data),
        'active_jobs': active_jobs,
        'stock_holding_job': stock_holding_job,
    }
    
    return render(request, 'purchases/use_stock.html', context)