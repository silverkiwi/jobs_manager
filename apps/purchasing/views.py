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
from django.http import HttpResponseRedirect, JsonResponse, FileResponse, Http404
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

# Add stock-related imports
from apps.purchasing.models import Stock
from apps.job.models import JobPricing, MaterialEntry
from apps.workflow.enums import JobPricingStage
from apps.workflow.utils import get_active_jobs
from decimal import Decimal, InvalidOperation

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
    
    template_name = 'purchases/delivery_receipt_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        purchase_order = get_object_or_404(PurchaseOrder, pk=kwargs['pk'])
        
        if purchase_order.status not in ['submitted', 'partially_received']:
            raise ValueError("This purchase order cannot be received")
            
        context['purchase_order'] = purchase_order
        context['title'] = f'Delivery Receipt - {purchase_order.po_number}'
        
        # Get stock holding job info
        from apps.job.models import Job
        try:
            stock_holding_job = Job.objects.get(is_stock_holding_job=True)
            context['stock_holding_job_id'] = stock_holding_job.id
            context['stock_holding_job_name'] = stock_holding_job.name
        except Job.DoesNotExist:
            context['stock_holding_job_id'] = ''
            context['stock_holding_job_name'] = 'Stock Holding Job'
            
        return context


@require_http_methods(["POST"])
def process_delivery_receipt_view(request):
    """Process a delivery receipt submission."""
    try:
        data = json.loads(request.body)
        purchase_order_id = data.get('purchase_order_id')
        line_allocations = data.get('line_allocations', {})
        
        if not purchase_order_id:
            return JsonResponse({'success': False, 'error': 'Purchase order ID is required'})
            
        from .services.delivery_receipt_service import process_delivery_receipt
        
        with transaction.atomic():
            success = process_delivery_receipt(purchase_order_id, line_allocations)
            
        if success:
            return JsonResponse({'success': True, 'message': 'Delivery receipt processed successfully'})
        else:
            return JsonResponse({'success': False, 'error': 'Failed to process delivery receipt'})
            
    except Exception as e:
        logger.error(f"Error processing delivery receipt: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


class StockListView(LoginRequiredMixin, ListView):
    """REST API view to list all active stock items."""
    
    model = Stock
    template_name = 'purchasing/stock_list.html'
    context_object_name = 'stock_items'
    
    def get_queryset(self):
        """Return active stock items ordered by description."""
        return Stock.objects.filter(is_active=True).order_by('description')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Stock Items'
        return context


class StockCreateView(LoginRequiredMixin, TemplateView):
    """REST API view to create new stock items."""
    
    template_name = 'purchasing/stock_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Stock Item'
        return context


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
            # Calculate unit revenue using the materials markup
            unit_revenue = item.unit_cost * (1 + materials_markup)
            total_value = item.quantity * item.unit_cost
            
            stock_data.append({
                'id': str(item.id),  # Convert UUID to string
                'description': item.description,
                'quantity': float(item.quantity),
                'unit_cost': float(item.unit_cost),
                'unit_revenue': float(unit_revenue),
                'total_value': float(total_value),
                'metal_type': item.metal_type,
                'alloy': item.alloy or '',
                'specifics': item.specifics or '',
                'location': item.location or ''
            })
        
        # If job_id is provided, get the job object to pass to the template
        default_job = None
        if job_id:
            try:
                default_job = next((job for job in active_jobs if str(job.id) == str(job_id)), None)
            except Exception as e:
                logger.error(f"Error finding job with ID {job_id}: {e}")
        
        context.update({
            'title': 'Use Stock',
            'stock_items': stock_items,
            'stock_data_json': json.dumps(stock_data),
            'active_jobs': active_jobs,
            'stock_holding_job': stock_holding_job,
            'default_job_id': str(job_id) if job_id else None,
        })
        
        return context


# Stock API Views - migrated from workflow
@require_http_methods(["POST"])
@transaction.atomic
def consume_stock_api_view(request):
    """
    API endpoint to record stock consumption for a job and create a MaterialEntry.
    """
    try:
        data = json.loads(request.body)
        job_id = data.get('job_id')
        stock_item_id = data.get('stock_item_id')
        quantity_used_str = data.get('quantity_used')

        # --- Validation ---
        if not all([job_id, stock_item_id, quantity_used_str]):
            logger.warning("Consume stock request missing required data.")
            return JsonResponse({'error': "Missing required data."}, status=400)

        try:
            quantity_used = Decimal(str(quantity_used_str))
            if quantity_used <= 0:
                 logger.warning(f"Invalid quantity used ({quantity_used}) for stock {stock_item_id}.")
                 return JsonResponse({'error': "Quantity used must be positive."}, status=400)
        except (InvalidOperation, TypeError):
            logger.warning(f"Invalid quantity format received: {quantity_used_str}")
            return JsonResponse({'error': "Invalid quantity format."}, status=400)

        job = get_object_or_404(Job, id=job_id) # Raises 404 if not found
        stock_item = get_object_or_404(Stock, id=stock_item_id) # Raises 404 if not found

        if quantity_used > stock_item.quantity:
            logger.warning(f"Attempted to consume {quantity_used} from stock {stock_item_id} with only {stock_item.quantity} available.")
            return JsonResponse({'error': f"Quantity used exceeds available stock ({stock_item.quantity})."}, status=400)

        reality_pricing = JobPricing.objects.filter(job=job, pricing_stage=JobPricingStage.REALITY).first()
        if not reality_pricing:
             logger.error(f"CRITICAL: 'Reality' JobPricing not found for job {job.id} during stock consumption.")
             # Return 500 as this is a system setup issue
             return JsonResponse({'error': f"Cannot record material cost: Reality pricing missing for job {job.id}"}, status=500)

        # --- Apply Business Logic / Pricing Rules ---
        # TODO: Implement specific pricing rules (e.g., half-sheet rule) here
        unit_cost = stock_item.unit_cost
        unit_revenue = unit_cost * (1 + stock_item.retail_rate)

        # --- Perform Database Operations ---
        material_entry = MaterialEntry.objects.create(
            job_pricing=reality_pricing,
            source_stock=stock_item,
            description=f"Consumed: {stock_item.description}",
            quantity=quantity_used,
            unit_cost=unit_cost,
            unit_revenue=unit_revenue,
            purchase_order_line=stock_item.source_purchase_order_line,
        )
        logger.info(f"Created MaterialEntry {material_entry.id} for Job {job_id} from Stock {stock_item_id}")

        stock_item.quantity -= quantity_used
        
        # If quantity is now zero, set is_active to False
        if stock_item.quantity <= 0:
            stock_item.is_active = False
            stock_item.save(update_fields=['quantity', 'is_active'])
            logger.info(f"Updated Stock {stock_item_id} quantity to {stock_item.quantity} and deactivated it")
        else:
            stock_item.save(update_fields=['quantity'])
            logger.info(f"Updated Stock {stock_item_id} quantity to {stock_item.quantity}")

        # --- Prepare Success Response ---
        response_data = {
            'success': True,
            'message': 'Stock consumed successfully.',
            # Include data needed to refresh the AG Grid on the frontend
            'new_material_entry': {
                'id': str(material_entry.id),
                'description': material_entry.description,
                'quantity': float(material_entry.quantity),
                'unit_cost': float(material_entry.unit_cost),
                'unit_revenue': float(material_entry.unit_revenue),
                'cost': float(material_entry.cost),
                'revenue': float(material_entry.revenue),
                'po_url': None # TODO: Generate PO URL if needed
            }
        }
        return JsonResponse(response_data, status=200) # Use 200 for successful update/action

    except json.JSONDecodeError:
        logger.warning("Invalid JSON received for stock consumption.")
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)
    except Http404 as e: # Catch 404 from get_object_or_404
         logger.warning(f"Not Found error during stock consumption: {e}")
         return JsonResponse({'error': str(e)}, status=404)
    except Exception as e:
        logger.exception(f"Unexpected error consuming stock: {e}")
        return JsonResponse({'error': 'An unexpected server error occurred.'}, status=500)


@require_http_methods(["POST"])
@transaction.atomic
def create_stock_api_view(request):
    """
    API endpoint to create a new stock item.
    """
    try:
        data = json.loads(request.body)
        description = data.get('description')
        quantity_str = data.get('quantity')
        unit_cost_str = data.get('unit_cost')
        source = data.get('source')
        notes = data.get('notes', '')
        metal_type = data.get('metal_type', '')
        alloy = data.get('alloy', '')
        specifics = data.get('specifics', '')
        location = data.get('location', '')

        # --- Validation ---
        if not all([description, quantity_str, unit_cost_str, source]):
            logger.warning("Create stock request missing required data.")
            return JsonResponse({'error': "Missing required data."}, status=400)

        try:
            quantity = Decimal(str(quantity_str))
            if quantity <= 0:
                logger.warning(f"Invalid quantity ({quantity}) for new stock.")
                return JsonResponse({'error': "Quantity must be positive."}, status=400)
        except (InvalidOperation, TypeError):
            logger.warning(f"Invalid quantity format received: {quantity_str}")
            return JsonResponse({'error': "Invalid quantity format."}, status=400)

        try:
            unit_cost = Decimal(str(unit_cost_str))
            if unit_cost <= 0:
                logger.warning(f"Invalid unit cost ({unit_cost}) for new stock.")
                return JsonResponse({'error': "Unit cost must be positive."}, status=400)
        except (InvalidOperation, TypeError):
            logger.warning(f"Invalid unit cost format received: {unit_cost_str}")
            return JsonResponse({'error': "Invalid unit cost format."}, status=400)

        # Get the stock holding job
        stock_holding_job = Stock.get_stock_holding_job()

        # Get company defaults for markup calculation
        from apps.workflow.models.company_defaults import CompanyDefaults
        company_defaults = CompanyDefaults.get_instance()
        materials_markup = company_defaults.materials_markup

        # Create the stock item
        stock_item = Stock.objects.create(
            job=stock_holding_job,
            description=description,
            quantity=quantity,
            unit_cost=unit_cost,
            source=source,
            notes=notes,
            metal_type=metal_type,
            alloy=alloy,
            specifics=specifics,
            location=location,
            is_active=True
        )
        logger.info(f"Created new Stock item {stock_item.id}: {description}")

        # Calculate unit revenue using the materials markup
        unit_revenue = unit_cost * (1 + materials_markup)
        total_value = quantity * unit_cost

        # Prepare response data
        response_data = {
            'success': True,
            'message': 'Stock item created successfully.',
            'stock_item': {
                'id': str(stock_item.id),
                'description': stock_item.description,
                'quantity': float(stock_item.quantity),
                'unit_cost': float(stock_item.unit_cost),
                'unit_revenue': float(unit_revenue),
                'total_value': float(total_value),
                'metal_type': stock_item.metal_type,
                'alloy': stock_item.alloy,
                'specifics': stock_item.specifics,
                'location': stock_item.location
            }
        }
        return JsonResponse(response_data, status=201)  # Use 201 for resource creation

    except json.JSONDecodeError:
        logger.warning("Invalid JSON received for stock creation.")
        return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)
    except Exception as e:
        logger.exception(f"Unexpected error creating stock: {e}")
        return JsonResponse({'error': 'An unexpected server error occurred.'}, status=500)


@require_http_methods(["GET"])
def search_available_stock_api(request):
    """
    API endpoint to search available stock items for autocomplete.
    Searches active stock items matching the search term.
    Relies on is_active=True implicitly meaning quantity > 0 and
    item is available for consumption (likely linked to Worker Admin job).
    """
    search_term = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 25)) # Limit results

    results = [] # Default to empty list

    if search_term:
        # Filter only by active status and description
        # Assumes is_active=True implies quantity > 0 and correct job allocation
        matching_stock = Stock.objects.filter(
            is_active=True,
            description__icontains=search_term
        ).select_related('job').order_by('description')[:limit] # Keep select_related for job name display

        # Serialize the data for autocomplete
        results = [
            {
                'id': str(item.id),
                # Display job name in text for clarity if needed, assuming active stock is under Worker Admin
                'text': f"{item.description} (Avail: {item.quantity}, Loc: {item.job.name if item.job else 'N/A'})",
                'description': item.description,
                'quantity': float(item.quantity),
                'unit_cost': float(item.unit_cost),
            }
            for item in matching_stock
        ]

    # Return results directly, matching ClientSearch response structure
    return JsonResponse({'results': results})


@require_http_methods(["POST"])
@transaction.atomic
def deactivate_stock_api_view(request, stock_id):
    """
    API endpoint to deactivate a stock item (soft delete).
    Sets is_active=False to hide it from the UI.
    """
    try:
        # Get the stock item
        stock_item = get_object_or_404(Stock, id=stock_id)
        
        # Set is_active to False (soft delete)
        stock_item.is_active = False
        stock_item.save(update_fields=['is_active'])
        
        logger.info(f"Deactivated Stock item {stock_id}: {stock_item.description}")
        
        # Return success response
        return JsonResponse({
            'success': True,
            'message': 'Stock item deleted successfully.'
        })
    except Http404 as e:
        logger.warning(f"Stock item not found for deactivation: {stock_id}")
        return JsonResponse({'error': str(e)}, status=404)
    except Exception as e:
        logger.exception(f"Unexpected error deactivating stock: {e}")
        return JsonResponse({'error': 'An unexpected server error occurred.'}, status=500)
