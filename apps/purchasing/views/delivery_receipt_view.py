from django.views.generic import ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db import transaction
import json
import logging

from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine
from apps.job.models import Job
from apps.purchasing.services.delivery_receipt_service import process_delivery_receipt
from apps.workflow.utils import get_active_jobs

logger = logging.getLogger(__name__)

class DeliveryReceiptListView(LoginRequiredMixin, ListView):
    """View to list all purchase orders that can be received."""
    
    model = PurchaseOrder
    template_name = 'purchasing/delivery_receipt_list.html'
    context_object_name = 'purchase_orders'
    
    def get_queryset(self):
        """Return purchase orders that are submitted or partially received."""
        return PurchaseOrder.objects.filter(
            status__in=['submitted', 'partially_received']
        ).order_by('-order_date')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Delivery Receipts'
        return context


class DeliveryReceiptCreateView(LoginRequiredMixin, TemplateView):
    """View to create a delivery receipt for a purchase order."""
    
    template_name = 'purchasing/delivery_receipt_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        purchase_order = get_object_or_404(PurchaseOrder, pk=kwargs['pk'])
        
        if purchase_order.status not in ['submitted', 'partially_received']:
            raise ValueError("This purchase order cannot be received")
            
        context['purchase_order'] = purchase_order
        context['title'] = f'Delivery Receipt - {purchase_order.po_number}'
        
        # Get stock holding job details
        stock_holding_job = Job.objects.filter(
            name="Stock Holding Job"
        ).first()
        
        if stock_holding_job:
            context['stock_holding_job_id'] = stock_holding_job.id
            context['stock_holding_job_name'] = stock_holding_job.name
        
        # Get line items for the purchase order
        line_items = purchase_order.lines.all()
        context['line_items'] = line_items
        context['line_items_json'] = json.dumps([
            {
                'id': str(line.id),
                'description': line.description,
                'quantity': float(line.quantity),
                'unit_cost': float(line.unit_cost or 0),
                'job_id': str(line.job.id) if line.job else '',
                'job_name': line.job.name if line.job else '',
                'delivered_quantity': float(line.delivered_quantity or 0),
                'remaining_quantity': float(line.quantity - (line.delivered_quantity or 0)),
            }
            for line in line_items
        ])
        
        return context


@require_http_methods(["POST"])
def process_delivery_receipt_view(request):
    """Process a delivery receipt submission."""
    try:
        with transaction.atomic():
            data = json.loads(request.body)
            purchase_order_id = data.get('purchase_order_id')
            line_items_data = data.get('line_items', [])
            
            purchase_order = get_object_or_404(PurchaseOrder, pk=purchase_order_id)
            
            # Process the delivery receipt
            result = process_delivery_receipt(purchase_order, line_items_data)
            
            if result['success']:
                messages.success(request, result['message'])
                return JsonResponse({
                    'success': True,
                    'message': result['message'],
                    'redirect_url': '/purchasing/delivery-receipts/'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': result['message']
                }, status=400)
                
    except Exception as e:
        logger.error(f"Error processing delivery receipt: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f"Error processing delivery receipt: {str(e)}"
        }, status=500)
