import json
import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from workflow.models import Job, Stock, MaterialEntry, JobPricing
from workflow.enums import JobPricingStage

logger = logging.getLogger(__name__)

@login_required
@require_http_methods(["POST"])
@transaction.atomic # Ensure database operations are atomic
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
        unit_revenue = unit_cost # Placeholder - Replace with actual revenue calculation

        # --- Perform Database Operations ---
        material_entry = MaterialEntry.objects.create(
            job_pricing=reality_pricing,
            source_stock=stock_item,
            description=f"Consumed: {stock_item.description}",
            quantity=quantity_used,
            unit_cost=unit_cost,
            unit_revenue=unit_revenue,
            purchase_order_line=stock_item.source_purchase_order_line,
            comments=f"Consumed from stock item {stock_item.id}"
        )
        logger.info(f"Created MaterialEntry {material_entry.id} for Job {job_id} from Stock {stock_item_id}")

        stock_item.quantity -= quantity_used
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

# Note: Broad exception handling removed to strictly match ClientSearch style.
# Consider adding it back if more robustness is needed.