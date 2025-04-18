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
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError # Import transaction and IntegrityError
from django.utils import timezone


from workflow.models import PurchaseOrder, PurchaseOrderLine, PurchaseOrderSupplierQuote, Client, Job
from workflow.forms import PurchaseOrderForm, PurchaseOrderLineForm
from workflow.utils import extract_messages
from workflow.services.quote_to_po_service import save_quote_file, create_po_from_quote, extract_data_from_supplier_quote
from workflow.views.xero.xero_po_creator import XeroPurchaseOrderCreator

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
    """View to create or edit a purchase order, following the timesheet pattern."""
    
    template_name = 'purchases/purchase_order_form.html'
    
    def get(self, request, *args, **kwargs):
        # Check if we're editing an existing purchase order
        purchase_order_id = self.kwargs.get('pk')
        if not purchase_order_id:
            # Creating a new purchase order - reserve a PO number immediately
            purchase_order = PurchaseOrder(status="draft", order_date=timezone.now().date())
            purchase_order.save()  # This will generate a unique PO number
            # Redirect to the URL with the new PO's ID
            return redirect('edit_purchase_order', pk=purchase_order.id)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Since we've redirected if no pk, we can assume pk exists
        purchase_order_id = self.kwargs.get('pk')
        purchase_order = get_object_or_404(PurchaseOrder, id=purchase_order_id)
        context['title'] = f'Purchase Order {purchase_order.po_number}'
        context['purchase_order_id'] = str(purchase_order.id) # Pass ID to template

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
                'unit_cost': float(line.unit_cost) if line.unit_cost is not None else None,
                'price_tbc': line.price_tbc,
                'total': float(line.quantity * (line.unit_cost or 0)),
                "metal_type": line.metal_type or "unspecified",
                "alloy": line.alloy or "",
                "specifics": line.specifics or "",
                "location": line.location or "",
            } for line in line_items
        ])
        
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
                'job_display_name': job.job_display_name,
                'estimated_materials': float(job.latest_estimate_pricing.total_material_cost) if job.latest_estimate_pricing else 0 # Handle None case
            } for job in jobs
        ])
        
        
        # Add Xero details to the main context for template access
        context['xero_purchase_order_url'] = xero_online_url 
        context['xero_id'] = str(xero_id) if xero_id else None
        context['purchase_order_status'] = purchase_order_status
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
@transaction.atomic # Ensure atomicity for PO and lines processing
def autosave_purchase_order_view(request):
    """
    Handles autosave requests for purchase order data. Separates create and update logic.
    """
    request_timestamp = datetime.now().isoformat()
    try:
        data = json.loads(request.body.decode('utf-8', errors='ignore'))
        purchase_order_data = data.get("purchase_order", {})
        line_items = data.get("line_items", [])
        purchase_order_id = purchase_order_data.get("id")

        logger.info(
            f"[{request_timestamp}] autosave_purchase_order_view called. Incoming PO ID: {purchase_order_id}"
        )
        logger.debug("Request data: %s", json.dumps(data, indent=2))
        logger.debug(f"Number of line items: {len(line_items)}")

        # Get IDs of all line items being saved
        saved_line_ids = [item.get("id") for item in line_items if item.get("id")]

        # Delete any existing line items not in current dataset
        if not purchase_order_id:
            logger.error("CRITICAL: Attempted line item operation without PO ID")
            raise ValueError("Purchase Order ID is required for line item operations")
            
        PurchaseOrderLine.objects.filter(
            purchase_order_id=purchase_order_id
        ).exclude(
            id__in=saved_line_ids
        ).delete()


        purchase_order = None
        created = False

        # Validate PO ID exists (this endpoint only handles updates)
        if not purchase_order_id:
            logger.error("CRITICAL: Attempted PO operation without ID")
            raise ValueError("Purchase Order ID is required")
            
        # --- UPDATE PATH ---
        logger.info(f"Attempting to update Purchase Order with ID: {purchase_order_id} with data {purchase_order_data}")
        try:
            # Lock the row for update
            purchase_order = PurchaseOrder.objects.select_for_update().get(id=purchase_order_id)

            # Update fields from payload
            purchase_order.supplier_id = purchase_order_data.get("client_id", purchase_order.supplier_id)
            purchase_order.status = purchase_order_data.get("status", purchase_order.status)
            purchase_order.order_date = purchase_order_data.get("order_date", purchase_order.order_date)
            # Handle expected_delivery carefully - allow setting to None
            if "expected_delivery" in purchase_order_data:
                    purchase_order.expected_delivery = purchase_order_data.get("expected_delivery") or None
            purchase_order.reference = purchase_order_data.get("reference")

            purchase_order.save()
            
            # If the PO has a Xero ID, sync it to Xero
            if purchase_order.xero_id:
                try:
                    logger.info(f"Syncing purchase order {purchase_order.id} to Xero")
                    # Create a XeroPurchaseOrderCreator instance and update the document in Xero
                    creator = XeroPurchaseOrderCreator(purchase_order=purchase_order)
                    creator.create_document()
                    logger.info(f"Successfully synced purchase order {purchase_order.id} to Xero")
                except Exception as e:
                    logger.exception(f"Error syncing purchase order to Xero: {e}")
                    # Don't return an error response here, just log it and continue
                    # The local update was successful, and that's what matters most
            else:
                logger.info("Not updating PO in Xero as no Xero ID is present.")
            logger.info(f"Updated purchase order {purchase_order.po_number} | {purchase_order.reference}")
            created = False
        except PurchaseOrder.DoesNotExist:
            logger.error(f"Purchase Order with ID {purchase_order_id} not found for update.")
            messages.error(request, f"Purchase Order with ID {purchase_order_id} not found.")
            return JsonResponse({"error": "Purchase Order not found", "messages": extract_messages(request)}, status=404)
        except Exception as e:
                logger.exception(f"Error updating PO {purchase_order_id}: {e}")
                messages.error(request, f"Error updating purchase order: {e}")
                return JsonResponse({"error": f"Error updating purchase order: {e}", "messages": extract_messages(request)}, status=500)


        # --- Process Line Items (Common to Create and Update) ---
        if purchase_order: # Ensure PO exists before processing lines
            processed_line_ids = set()
            for item_data in line_items:
                line_id = item_data.get("id")
                try:
                    # Use update_or_create for lines
                    line, line_created = PurchaseOrderLine.objects.update_or_create(
                        id=line_id or None,
                        purchase_order=purchase_order, # Associate with the correct PO
                        defaults={
                            'job_id': item_data.get("job"),
                            'description': item_data.get("description"),
                            'quantity': item_data.get("quantity"),
                            'unit_cost': item_data.get("unit_cost"),
                            'price_tbc': item_data.get("price_tbc", False),
                            'metal_type': item_data.get("metal_type", "unspecified"),
                            'alloy': item_data.get("alloy", ""),
                            'specifics': item_data.get("specifics", ""),
                            'location': item_data.get("location", "")
                        }
                    )
                    processed_line_ids.add(str(line.id))
                    # logger.debug(f"{'Created' if line_created else 'Updated'} line item {line.id} for PO {purchase_order.po_number}")
                except Exception as e:
                    logger.exception(f"Error processing line item {item_data}: {e}")
                    messages.error(request, f"Error processing line item: {e}")
                    # Decide if this should be a fatal error for the whole request
                    return JsonResponse({"error": f"Error processing line item: {e}", "messages": extract_messages(request)}, status=500)

            logger.debug("Line items processed successfully")
        else:
             logger.error("Purchase order object is None after create/update logic. Cannot process lines.")
             return JsonResponse({"error": "Internal error: Purchase order not available after processing.", "messages": extract_messages(request)}, status=500)


        # --- Success Response ---
        response_data = {
            "success": True,
            "messages": extract_messages(request),
            "po_number": purchase_order.po_number,
            "id": str(purchase_order.id), # Crucial: Always return the ID
            "action": "created" if created else "updated",
        }
        logger.debug(f"Returning success response: {response_data}")
        return JsonResponse(response_data)

    except json.JSONDecodeError:
        logger.error("Failed to parse JSON in autosave request")
        messages.error(request, "Invalid request format.")
        return JsonResponse(
            {"error": "Invalid JSON", "messages": extract_messages(request)}, status=400
        )
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        logger.exception("Unexpected error during purchase order autosave")
        return JsonResponse(
            {"error": f"Unexpected server error: {str(e)}", "messages": extract_messages(request)}, status=500
        )
    

@require_http_methods(["POST"])
@transaction.atomic
def delete_purchase_order_view(request, pk):
    if not pk:
        return JsonResponse({
            "success": False,
            "error": "Missing PO id in the request."
        }, status=400)
    
    try:
        po: PurchaseOrder = PurchaseOrder.objects.get(id=pk)

        if po.status != "draft": raise Exception("Invalid PO status - cannot delete a PO that was already sent to supplier.")

        po.delete()

        return JsonResponse({
            "success": True,
        }, status=200)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"There was an error while trying to delete Purchase Order {pk}: {e}"
        })


@require_http_methods(["POST"])
def extract_supplier_quote_data_view(request):
    """
    Extract data from a supplier quote to pre-fill a PO form.
    
    Args:
        request: The HTTP request
        
    Returns:
        JsonResponse with the extracted data
    """
    try:
        # Check if a file was uploaded
        if 'quote_file' not in request.FILES:
            return JsonResponse({
                "success": False,
                "error": "No quote file uploaded."
            }, status=400)
        
        quote_file = request.FILES['quote_file']
        
        # Save the file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            for chunk in quote_file.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name
        
        try:
            # Extract data from the quote
            # Set use_pdf_parser to True to use pdfplumber
            quote_data, error = extract_data_from_supplier_quote(
                temp_path,
                quote_file.content_type
            )
            
            # Delete the temporary file
            os.unlink(temp_path)
            
            if error:
                return JsonResponse({
                    "success": False,
                    "error": f"Error extracting data from quote: {error}"
                }, status=400)
            
            # Extract supplier information if available
            supplier_id = None
            if quote_data.get("matched_supplier") and quote_data["matched_supplier"].get("id"):
                supplier_id = quote_data["matched_supplier"]["id"]
            
            # Create a draft PO with pre-filled data
            purchase_order = PurchaseOrder.objects.create(
                status="draft",
                order_date=timezone.now().date(),
                supplier_id=supplier_id,
                reference=quote_data.get("quote_reference")
            )
            
            # Create a PurchaseOrderSupplierQuote linked to the PO
            supplier_quote_id = uuid.uuid4()
            supplier_quote = PurchaseOrderSupplierQuote(
                id=supplier_quote_id,
                purchase_order=purchase_order,
                filename=quote_file.name,
                file_path=f"temp/{supplier_quote_id}_{quote_file.name}",
                mime_type=quote_file.content_type,
                extracted_data=quote_data
            )
            supplier_quote.save()
            
            # Create PO line items from the extracted data
            if quote_data.get("items"):
                for item in quote_data["items"]:
                    PurchaseOrderLine.objects.create(
                        purchase_order=purchase_order,
                        description=item.get("description", ""),
                        quantity=item.get("quantity", 1),
                        unit_cost=item.get("unit_price"),
                        price_tbc=item.get("unit_price") is None,
                        metal_type=item.get("metal_type", "unspecified"),
                        alloy=item.get("alloy", ""),
                        specifics=item.get("specifics", "")
                    )
            
            # Redirect to the PO form with the PO ID
            redirect_url = reverse('edit_purchase_order', kwargs={'pk': purchase_order.id})
            return redirect(redirect_url)
            
        except Exception as e:
            # Make sure to delete the temporary file in case of error
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e
        
    except Exception as e:
        logger.exception(f"Error extracting data from quote: {e}")
        return JsonResponse({
            "success": False,
            "error": f"Error extracting data from quote: {str(e)}"
        }, status=500)
