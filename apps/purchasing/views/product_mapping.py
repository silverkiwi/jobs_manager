import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from decimal import Decimal

from apps.quoting.models import ProductParsingMapping

logger = logging.getLogger(__name__)


def product_mapping_validation(request):
    """
    Modern interface for validating product parsing mappings.
    """
    # Get mappings that need validation (not validated yet)
    unvalidated_mappings = ProductParsingMapping.objects.filter(
        is_validated=False
    ).order_by("-created_at")[
        :100
    ]  # Increased limit for better search

    # Update Xero status for unvalidated mappings
    for mapping in unvalidated_mappings:
        mapping.update_xero_status()

    # Get recently validated mappings for context
    validated_mappings = ProductParsingMapping.objects.filter(
        is_validated=True
    ).order_by("-validated_at")[:20]

    # Update Xero status for validated mappings too
    for mapping in validated_mappings:
        mapping.update_xero_status()

    # Get some stats
    total_mappings = ProductParsingMapping.objects.count()
    validated_count = ProductParsingMapping.objects.filter(is_validated=True).count()
    unvalidated_count = total_mappings - validated_count

    context = {
        "title": "Product Mapping Validation",
        "unvalidated_mappings": unvalidated_mappings,
        "validated_mappings": validated_mappings,
        "stats": {
            "total_mappings": total_mappings,
            "validated_count": validated_count,
            "unvalidated_count": unvalidated_count,
            "validation_percentage": round(
                (validated_count / total_mappings * 100) if total_mappings > 0 else 0, 1
            ),
        },
    }

    return render(request, "purchasing/product_mapping_validation.html", context)


@require_http_methods(["POST"])
def validate_mapping(request, mapping_id):
    """
    Validate a product parsing mapping.
    """
    try:
        mapping = ProductParsingMapping.objects.get(id=mapping_id)

        # Update validation status
        mapping.is_validated = True
        mapping.validated_by = request.user
        mapping.validated_at = timezone.now()
        mapping.validation_notes = request.POST.get("validation_notes", "")

        # Update any modified mapping fields from the form
        mapping.mapped_item_code = request.POST.get(
            "mapped_item_code", mapping.mapped_item_code
        )
        mapping.mapped_description = request.POST.get(
            "mapped_description", mapping.mapped_description
        )
        mapping.mapped_metal_type = request.POST.get(
            "mapped_metal_type", mapping.mapped_metal_type
        )
        mapping.mapped_alloy = request.POST.get("mapped_alloy", mapping.mapped_alloy)
        mapping.mapped_specifics = request.POST.get(
            "mapped_specifics", mapping.mapped_specifics
        )
        mapping.mapped_dimensions = request.POST.get(
            "mapped_dimensions", mapping.mapped_dimensions
        )

        unit_cost = request.POST.get("mapped_unit_cost")
        if unit_cost:
            try:
                mapping.mapped_unit_cost = Decimal(unit_cost)
            except:
                pass

        mapping.mapped_price_unit = request.POST.get(
            "mapped_price_unit", mapping.mapped_price_unit
        )

        # Update Xero status based on the new item code
        mapping.update_xero_status()

        mapping.save()

        return JsonResponse(
            {"success": True, "message": "Mapping validated successfully"}
        )

    except ProductParsingMapping.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Mapping not found"}, status=404
        )
    except Exception as e:
        logger.exception(f"Error validating mapping {mapping_id}: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)
