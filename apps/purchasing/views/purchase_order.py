"""
Purchase Order views for the purchasing app.
RESTful API design with proper separation of concerns.
"""

import base64
import json
import logging
import os
import tempfile
import uuid

from datetime import datetime
from django.urls import reverse
from django.views.generic import ListView, CreateView, DetailView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import inlineformset_factory, Form
from django.http import HttpResponseRedirect, JsonResponse, Http404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine, PurchaseOrderSupplierQuote
from apps.client.models import Client
from apps.job.models import Job
from apps.purchasing.forms import PurchaseOrderForm, PurchaseOrderLineForm
from apps.workflow.models.company_defaults import CompanyDefaults
from apps.purchasing.services.purchase_order_pdf_service import create_purchase_order_pdf
from apps.workflow.utils import extract_messages
from apps.purchasing.services.quote_to_po_service import save_quote_file, create_po_from_quote, extract_data_from_supplier_quote
from apps.purchasing.services.purchase_order_email_service import create_purchase_order_email
from apps.workflow.views.xero.xero_po_manager import XeroPurchaseOrder, XeroPurchaseOrderManager

logger = logging.getLogger(__name__)


class PurchaseOrderListView(LoginRequiredMixin, ListView):
    """API view to list all purchase orders."""
    
    model = PurchaseOrder
    template_name = 'purchasing/purchase_order_list.html'
    context_object_name = 'purchase_orders'
    
    def get_queryset(self):
        """Return purchase orders ordered by date."""
        return PurchaseOrder.objects.all().order_by('-order_date')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Purchase Orders'
        return context


class PurchaseOrderCreateView(LoginRequiredMixin, TemplateView):
    """REST API view to create or edit a purchase order."""
    
    template_name = 'purchasing/purchase_order_form.html'
    
    def get(self, request, *args, **kwargs):
        # Check if we're editing an existing purchase order
        purchase_order_id = self.kwargs.get('pk')
        if not purchase_order_id:
            # Check if we have a quote_id in query params for creating PO from quote
            quote_id = request.GET.get('quote_id')
            if quote_id:
                try:
                    quote = get_object_or_404(PurchaseOrderSupplierQuote, id=quote_id)
                    # Create PO from quote
                    po = create_po_from_quote(quote)
                    return redirect(reverse('purchasing:purchase_order_edit', kwargs={'pk': po.id}))
                except Exception as e:
                    messages.error(request, f'Error creating PO from quote: {str(e)}')
                    return redirect(reverse('purchasing:purchase_order_list'))
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        
        # Check if we're editing an existing purchase order or creating a new one
        purchase_order_id = self.kwargs.get('pk')
        if purchase_order_id:
            # Editing existing purchase order
            purchase_order = get_object_or_404(PurchaseOrder, id=purchase_order_id)
            context['title'] = f'Purchase Order {purchase_order.po_number}'
            context['purchase_order_id'] = str(purchase_order.id)
        else:
            # Creating new purchase order
            purchase_order = None
            context['title'] = 'New Purchase Order'
            context['purchase_order_id'] = None

        # Add supplier quote to context (it's a OneToOneField, not a collection)
        try:
            # Implementation for supplier quote
            pass
        except PurchaseOrder.supplier_quote.RelatedObjectDoesNotExist:
            pass
        
        # Fetch Xero details if available
        xero_online_url = purchase_order.online_url
        xero_id = purchase_order.xero_id
        purchase_order_status = purchase_order.status

        # Add purchase order data
        context['purchase_order_json'] = json.dumps({
            'id': str(purchase_order.id),
            'po_number': purchase_order.po_number,
            'supplier': str(purchase_order.supplier.id) if purchase_order.supplier else None,
            'supplier_name': purchase_order.supplier.name if purchase_order.supplier else None,
            'client_xero_id': purchase_order.supplier.xero_contact_id if purchase_order.supplier and purchase_order.supplier.xero_contact_id else None,
            'order_date': purchase_order.order_date.isoformat() if purchase_order.order_date else None,
            'expected_delivery': purchase_order.expected_delivery.isoformat() if purchase_order.expected_delivery else None,
            'status': purchase_order_status,
            'xero_id': str(xero_id) if xero_id else None,
            'xero_online_url': xero_online_url,
            'reference': purchase_order.reference if purchase_order.reference else None
        })

        # Get line items for this purchase order
        assert isinstance(purchase_order, PurchaseOrder)
        line_items = purchase_order.po_lines.all()
        context['line_items_json'] = json.dumps([
            {
                'id': str(line.id),
                'job': str(line.job.id) if line.job else None,
                'job_display_name': line.job.job_display_name if line.job else None,
                'description': line.description,
                'quantity': float(line.quantity),
                'unit_cost': float(line.unit_cost),
                'price_tbc': line.price_tbc,
                'metal_type': line.metal_type,
                'alloy': line.alloy,
                'specifics': line.specifics,
                'location': line.location,
            }
            for line in line_items
        ])

        # Add jobs and clients for dropdowns
        context['jobs'] = Job.objects.filter(status__in=['active', 'pending', 'in_progress', 'invoiced']).order_by('title')
        context['clients'] = Client.objects.all().order_by('name')
        
        return context

    def post(self, request, *args, **kwargs):
        """Handle form submission via AJAX."""
        try:
            # Implementation for form submission
            pass
        except Exception as e:
            logger.error(f"Error in PurchaseOrderCreateView POST: {e}")
            return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
@transaction.atomic
def autosave_purchase_order_view(request):
    """REST API endpoint to autosave purchase order data."""
    try:
        # Implementation for autosave
        pass
    except Exception as e:
        logger.error(f"Error in autosave_purchase_order_view: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
def delete_purchase_order_view(request, pk):
    """REST API endpoint to delete a purchase order."""
    try:
        # Implementation for delete
        pass
    except Exception as e:
        logger.error(f"Error in delete_purchase_order_view: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
def extract_supplier_quote_data_view(request):
    """REST API endpoint to extract data from a supplier quote to pre-fill a PO form."""
    try:
        # Implementation for quote extraction
        pass
    except Exception as e:
        logger.error(f"Error in extract_supplier_quote_data_view: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


class PurchaseOrderPDFView(APIView):
    """REST API view for generating and returning PDF documents for purchase orders."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Generate and return a PDF for the specified purchase order."""
        try:
            # Implementation for PDF generation
            pass
        except Exception as e:
            logger.error(f"Error in PurchaseOrderPDFView: {e}")
            raise Http404("Purchase order not found")


class PurchaseOrderEmailView(APIView):
    """REST API view for generating email links for purchase orders."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Generate and return email details for the specified purchase order."""
        try:
            # Implementation for email generation
            pass
        except Exception as e:
            logger.error(f"Error in PurchaseOrderEmailView: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
