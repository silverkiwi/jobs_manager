from django.views.generic import ListView, CreateView, DetailView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import inlineformset_factory, Form
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
import json
import logging

from workflow.models import PurchaseOrder, PurchaseOrderLine, Client, Job
from workflow.forms import PurchaseOrderForm, PurchaseOrderLineForm
from workflow.utils import extract_messages

logger = logging.getLogger(__name__)


class PurchaseOrderListView(LoginRequiredMixin, ListView):
    """View to list all purchase orders."""
    
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
    """View to create a new purchase order, following the timesheet pattern."""
    
    template_name = 'purchases/purchase_order_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'New Purchase Order'
        
        # Get active jobs for the line items - match exactly what timesheet view does
        jobs = Job.objects.filter(
            status__in=['quoting', 'approved', 'in_progress', 'special']
        ).select_related('client', 'latest_estimate_pricing')
        
        context['jobs_json'] = json.dumps([
            {
                'id': str(job.id),
                'job_number': job.job_number,
                'name': job.name,
                'client_name': job.client.name if job.client else 'No Client',
                'client_id': str(job.client.id) if job.client else None,
                'job_display_name': f"{job.job_number} - {job.name}",
                'estimated_materials': float(job.latest_estimate_pricing.total_material_cost)
            } for job in jobs
        ])
        
        # Empty line items array for new purchase orders
        # This follows the timesheet pattern where we pass existing entries
        context['line_items_json'] = json.dumps([])
        
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
                'redirect_url': reverse_lazy('purchase_orders')
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)


# Kept for reference but not used directly anymore
PurchaseOrderLineFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderLine,
    form=PurchaseOrderLineForm,
    extra=1,
    can_delete=True
)


@require_http_methods(["POST"])
def autosave_purchase_order_view(request):
    """
    Handles autosave requests for purchase order data.
    
    Purpose:
    - Automates the saving of purchase order changes, including updates, creations, and deletions.
    - Ensures data consistency and prevents duplication during processing.
    - Follows the same pattern as timesheet autosave for consistency.
    
    Workflow:
    1. Parsing and Validation:
    - Parses the incoming request body as JSON.
    - Extracts purchase order data and line items.
    
    2. Processing:
    - Creates or updates the purchase order.
    - Creates or updates line items.
    - Handles deletions of line items.
    
    3. Response:
    - Returns success responses with feedback messages.
    - Sends error responses for invalid data or unexpected issues.
    
    Parameters:
    - `request` (HttpRequest): The HTTP POST request containing purchase order data in JSON format.
    
    Returns:
    - JsonResponse: Contains success status, messages, and updated data.
    """
    try:
        logger.debug("Purchase order autosave request received")
        data = json.loads(request.body)
        logger.debug("Request data: %s", json.dumps(data, indent=2))
        
        purchase_order_data = data.get("purchase_order", {})
        line_items = data.get("line_items", [])
        deleted_line_items = data.get("deleted_line_items", [])
        
        logger.debug(f"Number of line items: {len(line_items)}")
        logger.debug(f"Number of items to delete: {len(deleted_line_items)}")
        
        # Handle deletions first, just like timesheet view does
        if deleted_line_items:
            for line_id in deleted_line_items:
                logger.debug(f"Deleting line item with ID: {line_id}")
                
                try:
                    line = PurchaseOrderLine.objects.get(id=line_id)
                    messages.success(request, "Line item deleted successfully")
                    line.delete()
                    logger.debug(f"Line item with ID {line_id} deleted successfully")
                except PurchaseOrderLine.DoesNotExist:
                    logger.error(f"Line item with ID {line_id} not found for deletion")
            
            return JsonResponse(
                {
                    "success": True,
                    "action": "remove",
                    "messages": extract_messages(request),
                },
                status=200,
            )
        
        # Validate we have something to process
        if not line_items and not deleted_line_items:
            logger.error("No valid items to process")
            messages.info(request, "No changes to save.")
            return JsonResponse(
                {
                    "error": "No line items provided",
                    "messages": extract_messages(request),
                },
                status=400,
            )
        
        # Get or create purchase order
        po_id = purchase_order_data.get("id")
        client_id = purchase_order_data.get("client_id")
        
        if not client_id:
            messages.error(request, "Supplier is required")
            return JsonResponse(
                {"error": "Supplier is required", "messages": extract_messages(request)},
                status=400,
            )
        
        if po_id:
            # Update existing purchase order
            try:
                purchase_order = PurchaseOrder.objects.get(id=po_id)
                purchase_order.supplier_id = client_id
                purchase_order.expected_delivery = purchase_order_data.get("expected_delivery")
                purchase_order.save()
                logger.debug(f"Updated purchase order {purchase_order.po_number}")
            except PurchaseOrder.DoesNotExist:
                logger.error(f"Purchase order with ID {po_id} not found")
                messages.error(request, f"Purchase order not found")
                return JsonResponse(
                    {"error": f"Purchase order not found", "messages": extract_messages(request)},
                    status=404,
                )
        else:
            # Create new purchase order
            from datetime import datetime
            purchase_order = PurchaseOrder(
                supplier_id=client_id,
                order_date=purchase_order_data.get("order_date") or datetime.now().date(),
                expected_delivery=purchase_order_data.get("expected_delivery"),
                status="draft"
            )
            purchase_order.save()
            logger.debug(f"Created new purchase order {purchase_order.po_number}")
        
        # Process line items - similar to timesheet entry processing
        updated_lines = []
        for item_data in line_items:
            if not item_data.get("job") or not item_data.get("description"):
                logger.debug("Skipping incomplete line item: ", item_data)
                continue
                
            line_id = item_data.get("id")
            logger.debug(f"Processing line item: {json.dumps(item_data, indent=2)}")
            
            if line_id and line_id != "tempId":
                try:
                    logger.debug(f"Processing line item with ID: {line_id}")
                    line = PurchaseOrderLine.objects.get(id=line_id)
                    
                    # Update existing line
                    line.job_id = item_data.get("job")
                    line.description = item_data.get("description")
                    line.quantity = item_data.get("quantity", 1)
                    line.unit_cost = item_data.get("unit_cost", 0) if item_data.get("unit_cost") != "TBC" else 0
                    line.save()
                    
                    updated_lines.append(line)
                    messages.success(request, "Line item updated successfully")
                    logger.debug("Line item updated successfully")
                    
                    return JsonResponse(
                        {
                            "success": True,
                            "po_number": purchase_order.po_number,
                            "id": str(purchase_order.id),
                            "action": "update",
                            "messages": extract_messages(request),
                        },
                        status=200,
                    )
                    
                except PurchaseOrderLine.DoesNotExist:
                    logger.error(f"Line item with ID {line_id} not found")
            else:
                # Create new line
                line = PurchaseOrderLine.objects.create(
                    purchase_order=purchase_order,
                    job_id=item_data.get("job"),
                    description=item_data.get("description"),
                    quantity=item_data.get("quantity", 1),
                    unit_cost=item_data.get("unit_cost", 0) if item_data.get("unit_cost") != "TBC" else 0
                )
                
                updated_lines.append(line)
                messages.success(request, "Line item created successfully")
                logger.debug("Line item created successfully")
                
                return JsonResponse(
                    {
                        "success": True,
                        "po_number": purchase_order.po_number,
                        "id": str(purchase_order.id),
                        "action": "add",
                        "messages": extract_messages(request),
                    },
                    status=200,
                )
        
        return JsonResponse(
            {
                "success": True,
                "messages": extract_messages(request),
                "po_number": purchase_order.po_number,
                "id": str(purchase_order.id),
                "action": "update",
            }
        )
        
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON")
        messages.error(request, "Failed to parse JSON")
        return JsonResponse(
            {"error": "Invalid JSON", "messages": extract_messages(request)}, status=400
        )
    
    except Exception as e:
        messages.error(request, f"Unexpected error: {str(e)}")
        logger.exception("Unexpected error during purchase order autosave")
        return JsonResponse(
            {"error": str(e), "messages": extract_messages(request)}, status=500
        )