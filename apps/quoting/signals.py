import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import SupplierProduct
from .services.product_parser import ProductParser
from apps.purchasing.models import Stock

logger = logging.getLogger(__name__)


@receiver(post_save, sender=SupplierProduct)
def auto_parse_supplier_product(sender, instance, created, **kwargs):
    """
    Automatically parse supplier products when they're created or updated.
    This ensures mappings are optimistically populated as data comes in.
    """
    if not created and instance.parsed_at:
        # Skip if this is an update and it's already been parsed
        return
    
    try:
        # Prepare product data for parsing
        product_data = {
            'product_name': instance.product_name,
            'description': instance.description or '',
            'specifications': instance.specifications or '',
            'item_no': instance.item_no,
            'variant_id': instance.variant_id,
            'variant_width': instance.variant_width or '',
            'variant_length': instance.variant_length or '',
            'variant_price': instance.variant_price,
            'price_unit': instance.price_unit or '',
        }
        
        # Parse the product
        parser = ProductParser()
        parsed_data, was_cached = parser.parse_product(product_data)
        
        if parsed_data:
            # Update the product with parsed data
            instance.parsed_item_code = parsed_data.get('item_code')
            instance.parsed_description = parsed_data.get('description')
            instance.parsed_metal_type = parsed_data.get('metal_type')
            instance.parsed_alloy = parsed_data.get('alloy')
            instance.parsed_specifics = parsed_data.get('specifics')
            instance.parsed_dimensions = parsed_data.get('dimensions')
            instance.parsed_unit_cost = parsed_data.get('unit_cost')
            instance.parsed_price_unit = parsed_data.get('price_unit')
            instance.parsed_at = timezone.now()
            instance.parser_version = parsed_data.get('parser_version')
            instance.parser_confidence = parsed_data.get('confidence')
            
            # Save without triggering signals again
            SupplierProduct.objects.filter(id=instance.id).update(
                parsed_item_code=instance.parsed_item_code,
                parsed_description=instance.parsed_description,
                parsed_metal_type=instance.parsed_metal_type,
                parsed_alloy=instance.parsed_alloy,
                parsed_specifics=instance.parsed_specifics,
                parsed_dimensions=instance.parsed_dimensions,
                parsed_unit_cost=instance.parsed_unit_cost,
                parsed_price_unit=instance.parsed_price_unit,
                parsed_at=instance.parsed_at,
                parser_version=instance.parser_version,
                parser_confidence=instance.parser_confidence,
            )
            
            status = "from cache" if was_cached else "newly parsed"
            logger.info(f"Auto-parsed supplier product {instance.id} ({status})")
        else:
            logger.warning(f"Failed to auto-parse supplier product {instance.id}")
            
    except Exception as e:
        logger.exception(f"Error auto-parsing supplier product {instance.id}: {e}")


@receiver(post_save, sender=Stock)
def auto_parse_stock_item(sender, instance, created, **kwargs):
    """
    Automatically parse Stock items when they're created or updated.
    Many inventory items only have descriptions and missing details like
    metal_type, alloy, specifics that can be inferred from the description.
    """
    if not created and instance.parsed_at:
        # Skip if this is an update and it's already been parsed
        return
    
    try:
        # Prepare stock data for parsing - use description as main input
        stock_data = {
            'product_name': instance.description or '',
            'description': instance.description or '',
            'specifications': instance.specifics or '',
            'item_no': instance.item_code or '',
            'variant_id': f"stock-{instance.id}",  # Unique identifier
            'variant_width': '',
            'variant_length': '',
            'variant_price': instance.unit_cost,
            'price_unit': 'each',  # Default for stock items
        }
        
        # Parse the stock item
        parser = ProductParser()
        parsed_data, was_cached = parser.parse_product(stock_data)
        
        if parsed_data:
            # Only update fields that are currently blank/unspecified
            updates = {
                'parsed_at': timezone.now(),
                'parser_version': parsed_data.get('parser_version'),
                'parser_confidence': parsed_data.get('confidence'),
            }
            
            if not instance.metal_type or instance.metal_type == 'unspecified':
                if parsed_data.get('metal_type'):
                    updates['metal_type'] = parsed_data['metal_type']
            
            if not instance.alloy:
                if parsed_data.get('alloy'):
                    updates['alloy'] = parsed_data['alloy']
            
            if not instance.specifics:
                if parsed_data.get('specifics'):
                    updates['specifics'] = parsed_data['specifics']
            
            # Always update item_code if we have a better one
            if parsed_data.get('item_code') and not instance.item_code:
                updates['item_code'] = parsed_data['item_code']
            
            # Apply updates
            Stock.objects.filter(id=instance.id).update(**updates)
            status = "from cache" if was_cached else "newly parsed"
            updated_fields = [k for k in updates.keys() if k not in ['parsed_at', 'parser_version', 'parser_confidence']]
            logger.info(f"Auto-parsed stock item {instance.id} ({status}): {updated_fields}")
        else:
            logger.warning(f"Failed to auto-parse stock item {instance.id}")
            
    except Exception as e:
        logger.exception(f"Error auto-parsing stock item {instance.id}: {e}")