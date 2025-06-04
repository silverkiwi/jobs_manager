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
from django.http import HttpResponseRedirect, JsonResponse, FileResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

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
    template_name = 'purchases/purchase_order_list.html'
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
    
    template_name = 'purchases/purchase_order_form.html'
    
    def get(self, request, *args, **kwargs):
        # Check if we're editing an existing purchase order
        purchase_order_id = self.kwargs.get('pk')
        if not purchase_order_id:
            # Creating a new purchase order - reserve a PO number immediately
            purchase_order = PurchaseOrder(status="draft", order_date=timezone.now().date())
            purchase_order.save()  # This will generate a unique PO number
            # Redirect to the URL with the new PO's ID
            return redirect('purchasing:purchase_orders_detail', pk=purchase_order.id)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Since we've redirected if no pk, we can assume pk exists
        purchase_order_id = self.kwargs.get('pk')
        purchase_order = get_object_or_404(PurchaseOrder, id=purchase_order_id)
        context['title'] = f'Purchase Order {purchase_order.po_number}'
        context['purchase_order_id'] = str(purchase_order.id) # Pass ID to template

        # Add supplier quote to context (it's a OneToOneField, not a collection)
        try:
            context['supplier_quote'] = purchase_order.supplier_quote
        except PurchaseOrder.supplier_quote.RelatedObjectDoesNotExist:
            context['supplier_quote'] = None
        
        # Fetch Xero details if available
        xero_online_url = purchase_order.online_url
        xero_id = purchase_order.xero_id
        purchase_order_status = purchase_order.status # Fetch the status

        # Add purchase order data
        context['purchase_order_json'] = json.dumps({
            'id': str(purchase_order.id),
            'po_number': purchase_order.po_number,
            'supplier': str(purchase_order.supplier.id) if purchase_order.supplier else None,
            'supplier_name': purchase_order.supplier.name if purchase_order.supplier else None,
            'client_xero_id': purchase_order.supplier.xero_contact_id if purchase_order.supplier and purchase_order.supplier.xero_contact_id else None,
            'order_date': purchase_order.order_date.isoformat() if purchase_order.order_date else None,
            'expected_delivery': purchase_order.expected_delivery.isoformat() if purchase_order.expected_delivery else None,
            'status': purchase_order_status, # Use the fetched status
            'xero_id': str(xero_id) if xero_id else None, # Include Xero ID if exists
            'xero_online_url': xero_online_url, # Include Xero URL if exists,
            'reference': purchase_order.reference if purchase_order.reference else None
        })

        # Get line items for this purchase order
        assert isinstance(purchase_order, PurchaseOrder) # Ensure type for Pylance
        line_items = purchase_order.po_lines.all() # Use correct related_name 'po_lines'
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
            purchase_order_data = json.loads(request.POST.get('purchase_order_data', '{}'))
            line_items_data = json.loads(request.POST.get('line_items_data', '[]'))
            
            # Get the client (supplier)
            client_id = purchase_order_data.get('supplier')
            
            # Create purchase order
            purchase_order = PurchaseOrder(
                supplier_id=client_id,
                order_date=purchase_order_data.get('order_date'),
                expected_delivery=purchase_order_data.get('expected_delivery'),
                status='draft'
            )
            purchase_order.save()
            
            # Create line items
            for item in line_items_data:
                PurchaseOrderLine.objects.create(
                    purchase_order=purchase_order,
                    job_id=item.get('job'),
                    description=item.get('description'),
                    quantity=item.get('quantity'),
                    unit_cost=item.get('unit_cost')
                )
            
            messages.success(request, f"Purchase order {purchase_order.po_number} created successfully.")
            return JsonResponse({
                'success': True, 
                'redirect_url': reverse_lazy('purchasing:purchase_orders_list')
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


@require_http_methods(["POST"])
@transaction.atomic
def autosave_purchase_order_view(request):
    """REST API endpoint to autosave purchase order data."""
    try:
        purchase_order_id = request.POST.get("purchase_order_id")
        purchase_order_data = json.loads(request.POST.get("purchase_order_data", "{}"))
        line_items = json.loads(request.POST.get("line_items", "[]"))

        if not purchase_order_id:
            logger.error("Purchase Order ID is required.")
            return JsonResponse({"error": "Purchase Order ID is required", "messages": extract_messages(request)}, status=400)

        # Delete line items not in the current list
        saved_line_ids = [item.get("id") for item in line_items if item.get("id")]
        PurchaseOrderLine.objects.filter(purchase_order_id=purchase_order_id).exclude(id__in=saved_line_ids).delete()

        try:
            purchase_order = PurchaseOrder.objects.select_for_update().get(id=purchase_order_id)
        except PurchaseOrder.DoesNotExist:
            logger.error(f"Purchase Order with ID {purchase_order_id} not found.")
            return JsonResponse({"error": "Purchase Order not found", "messages": extract_messages(request)}, status=404)

        if "client_id" in purchase_order_data:
            purchase_order.supplier_id = purchase_order_data["client_id"]
        if "status" in purchase_order_data:
            purchase_order.status = purchase_order_data["status"]
        if "order_date" in purchase_order_data:
            purchase_order.order_date = purchase_order_data["order_date"]
        if "expected_delivery" in purchase_order_data:
            purchase_order.expected_delivery = purchase_order_data["expected_delivery"] or None
        if "reference" in purchase_order_data:
            purchase_order.reference = purchase_order_data["reference"]

        purchase_order.save()

        for item_data in line_items:
            line_id = item_data.get("id")
            PurchaseOrderLine.objects.update_or_create(
                id=line_id or None,
                purchase_order=purchase_order,
                defaults={
                    'job_id': item_data.get("job"),
                    'description': item_data.get("description"),
                    'quantity': item_data.get("quantity"),
                    'unit_cost': item_data.get("unit_cost"),
                    'price_tbc': item_data.get("price_tbc", False),
                    'metal_type': item_data.get("metal_type", "unspecified"),
                    'alloy': item_data.get("alloy", ""),
                    'specifics': item_data.get("specifics", ""),
                    'location': item_data.get("location", ""),
                }
            )

        return JsonResponse({"success": True, "messages": extract_messages(request)})

    except Exception as e:
        logger.error(f"Error autosaving purchase order: {e}")
        return JsonResponse({"error": str(e), "messages": extract_messages(request)}, status=500)


@require_http_methods(["POST"])
def delete_purchase_order_view(request, pk):
    """REST API endpoint to delete a purchase order."""
    try:
        purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
        purchase_order.delete()
        messages.success(request, f"Purchase order {purchase_order.po_number} deleted successfully.")
        return JsonResponse({'success': True, 'redirect_url': reverse_lazy('purchasing:purchase_orders_list')})
    except Exception as e:
        messages.error(request, f"Error deleting purchase order: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def extract_supplier_quote_data_view(request):
    """REST API endpoint to extract data from a supplier quote to pre-fill a PO form."""
    try:
        # Get the uploaded file from the request
        uploaded_file = request.FILES.get('quote_file')
        ai_provider = request.POST.get('ai_provider', 'openai')  # Default to OpenAI
        
        if not uploaded_file:
            return JsonResponse({
                "success": False,
                "error": "No file uploaded"
            }, status=400)

        # Save the file temporarily
        quote_file_path = save_quote_file(uploaded_file)
        
        # Extract data and create PO
        purchase_order, error = create_po_from_quote(
            quote_file_path=quote_file_path,
            ai_provider=ai_provider
        )

        if error:
            return JsonResponse({
                "success": False,
                "error": f"Error extracting data from quote: {error}"
            }, status=400)

        # Redirect to the PO form with the PO ID
        redirect_url = reverse('purchasing:purchase_orders_detail', kwargs={'pk': purchase_order.id})
        return redirect(redirect_url)

    except Exception as e:
        logger.exception(f"Error extracting data from quote: {e}")
        return JsonResponse({
            "success": False,
            "error": f"Error extracting data from quote: {str(e)}"
        }, status=500)


class PurchaseOrderPDFView(APIView):
    """REST API view for generating and returning PDF documents for purchase orders."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Generate and return a PDF for the specified purchase order."""
        try:
            # Retrieve the purchase order
            purchase_order = get_object_or_404(PurchaseOrder, pk=pk)
            
            # Generate the PDF using the service
            pdf_buffer = create_purchase_order_pdf(purchase_order)
            
            # Configure the response
            filename = f"PO_{purchase_order.po_number}.pdf"
            
            # Return as inline content or for download based on query parameter
            as_attachment = request.query_params.get('download', 'false').lower() == 'true'
            
            # Create the response with the PDF
            response = FileResponse(
                pdf_buffer,
                as_attachment=as_attachment,
                filename=filename,
                content_type='application/pdf'
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating PDF for purchase order {pk}: {e}")
            return Response(
                {"error": f"Failed to generate PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PurchaseOrderEmailView(APIView):
    """REST API view for generating email links for purchase orders."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Generate and return email details for the specified purchase order."""
        try:
            purchase_order = get_object_or_404(PurchaseOrder, pk=pk)

            email_data = create_purchase_order_email(purchase_order)

            pdf_buffer = create_purchase_order_pdf(purchase_order)
            pdf_content = pdf_buffer.getvalue()
            pdf_buffer.close()

            pdf_base64 = base64.b64encode(pdf_content).decode("utf-8")
            return JsonResponse({
                "success": True,
                "mailto_url": email_data["mailto_url"],
                "email": email_data["email"],
                "subject": email_data["subject"],
                "body": email_data["body"],
                "pdf_content": pdf_base64,
                "filename": f"PO_{purchase_order.po_number}.pdf"
            })

        except Exception as e:
            logger.error(f"Error generating email for purchase order {pk}: {e}")
            return JsonResponse({
                "success": False,
                "error": f"Failed to generate email: {str(e)}"
            }, status=500)
