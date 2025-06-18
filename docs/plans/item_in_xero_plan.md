# Item Code in Xero Plan

## Overview
Add a field `item_code_is_in_xero` to the `ProductParsingMapping` model to indicate whether the mapped item code already exists in the Xero inventory system (Stock model). This will help users quickly identify which product mappings correspond to existing inventory items versus new items that need to be created.

## Requirements
- Add boolean field `item_code_is_in_xero` to `ProductParsingMapping` model
- Field should be set to `True` if the `mapped_item_code` exists in the `Stock` model, `False` otherwise
- Make this field visible in the product mapping validation view at `/purchasing/product-mapping/`
- Provide visual indication (badge, icon, etc.) in the UI

## Implementation Plan

### 1. Model Changes
**File**: `apps/quoting/models.py`

- Add `item_code_is_in_xero` boolean field to `ProductParsingMapping` model
- Default value should be `False`
- Add a method or property to check if `mapped_item_code` exists in Stock model
- Consider adding this as a computed field that gets updated when needed

```python

item_code_is_in_xero = models.BooleanField(
    default=False,
    help_text="Whether the mapped item code exists in Xero inventory (Stock model)"
)

from apps.purchasing.models import Stock  # Remember to put all imports at the top of the file if possible
def update_xero_status(self):
    """Update the item_code_is_in_xero field based on Stock model."""
    if self.mapped_item_code:
        self.item_code_is_in_xero = Stock.objects.filter(
            item_code=self.mapped_item_code
        ).exists()
    else:
        self.item_code_is_in_xero = False
```

### 2. Database Migration
**File**: `apps/quoting/migrations/0010_productparsingmapping_item_code_is_in_xero.py`

- Create Django migration for the new boolean field
- Apply migration to add the column to the database

### 3. View Logic Updates
**File**: `apps/purchasing/views/product_mapping.py`

Update the `product_mapping_validation` view to:
- Import Stock model from `apps.purchasing.models`
- For each mapping, check if `mapped_item_code` exists in Stock
- Update the `item_code_is_in_xero` field accordingly
- Pass this information to the template context

```python
from apps.purchasing.models import Stock

def product_mapping_validation(request):
    # ... existing code ...
    
    # Update Xero status for unvalidated mappings
    for mapping in unvalidated_mappings:
        if mapping.mapped_item_code:
            mapping.item_code_is_in_xero = Stock.objects.filter(
                item_code=mapping.mapped_item_code
            ).exists()
        else:
            mapping.item_code_is_in_xero = False
        # Optionally save the updated status
        # mapping.save(update_fields=['item_code_is_in_xero'])
```

### 4. Template Updates
**File**: `apps/purchasing/templates/purchasing/product_mapping_validation.html`

Update the template to display the Xero status:
- Add visual indicator (badge or icon) showing whether item exists in Xero
- Consider adding this to the mapping header or near the item code field
- Possibly add filtering option by Xero status

```html
<!-- In the mapped output section, near the item code field -->
<div class="mb-2">
    <label class="form-label">Item Code</label>
    <div class="input-group">
        <input type="text" name="mapped_item_code" class="form-control form-control-sm" 
               value="{{ mapping.mapped_item_code|default:'' }}">
        <span class="input-group-text">
            {% if mapping.item_code_is_in_xero %}
                <span class="badge bg-success" title="Item exists in Xero">
                    <i class="bi bi-check-circle"></i> In Xero
                </span>
            {% else %}
                <span class="badge bg-secondary" title="Item not found in Xero">
                    <i class="bi bi-question-circle"></i> New Item
                </span>
            {% endif %}
        </span>
    </div>
</div>
```

### 5. Optional Enhancements

#### Performance Optimization
- Consider adding a management command to batch update all existing mappings
- Add database index on `Stock.item_code` if not already present
- Cache the Xero status to avoid repeated database queries

#### Filtering and Search
- Add filter option in the UI to show only mappings that are/aren't in Xero
- Update the search functionality to include Xero status

#### Additional Features
- Show count of how many mappings have items in Xero vs new items
- Add bulk actions to handle mappings differently based on Xero status

## Database Schema Impact

### New Field
```sql
ALTER TABLE quoting_productparsingmapping 
ADD COLUMN item_code_is_in_xero BOOLEAN DEFAULT FALSE;
```

### Related Tables
- `purchasing_stock` (Stock model) - referenced for item_code lookup
- Field relationships: `ProductParsingMapping.mapped_item_code` → `Stock.item_code`

## Testing Considerations

1. **Model Tests**
   - Test the `update_xero_status()` method
   - Verify field defaults and validation

2. **View Tests**
   - Test that Xero status is correctly determined
   - Verify template context includes the status

3. **Integration Tests**
   - Test the complete flow from mapping creation to status display
   - Verify performance with large datasets

## Migration Strategy

1. Create and apply the database migration
2. Optionally run a data migration or management command to populate existing records
3. Update views and templates
4. Test the complete functionality
5. Deploy to production

## Files to Modify

1. `apps/quoting/models.py` - Add field and helper method
2. `apps/quoting/migrations/0010_*.py` - Database migration (auto-generated)
3. `apps/purchasing/views/product_mapping.py` - Update view logic
4. `apps/purchasing/templates/purchasing/product_mapping_validation.html` - UI updates

## Notes

- The Stock model's `item_code` field is the Xero Item Code, so checking against this field determines if an item exists in Xero
- Consider the performance impact of checking Stock records for each mapping
- The field could be updated in real-time or cached and updated periodically
- This feature will help users distinguish between mappings for existing inventory vs new items that need to be created in Xero