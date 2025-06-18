# Product Mapping: Common Key Strategy

## Problem Statement

The Stock model uses `item_code` for Xero Item Codes (internal accounting identifiers), while SupplierProduct uses `item_no` for supplier SKU numbers (external supplier identifiers). These represent different identifier systems and need a common key for cross-referencing.

## Solution: Standardized Item Codes via AI Parsing

Use SupplierProduct's `parsed_item_code` field to generate standardized item codes that match Stock's `item_code` structure, creating a unified material identification system.

---

# Detailed Plan: Common Key via Standardized Item Codes

## Phase 1: Design Standardized Item Code Format

### 1.1 Item Code Structure Design
**Format**: `{METAL_TYPE}-{ALLOY}-{FORM}-{DIMENSIONS}-{SEQUENCE}`

Examples:
- `STL-304-SHT-3X1500X3000-001` (Stainless steel 304 sheet)
- `ALU-6061-BAR-25DIA-001` (Aluminum 6061 round bar)
- `STL-MS-ANG-50X50X5-001` (Mild steel angle)

### 1.2 Component Definitions
- **METAL_TYPE**: STL (steel), ALU (aluminum), BRS (brass), etc.
- **ALLOY**: 304, 6061, MS (mild steel), GAL (galvanized)
- **FORM**: SHT (sheet), BAR (bar), ANG (angle), TUB (tube)
- **DIMENSIONS**: Standardized format based on form type
- **SEQUENCE**: 3-digit incrementer for identical materials from different sources

### 1.3 Mapping Rules
```python
METAL_TYPE_MAP = {
    MetalType.STAINLESS_STEEL: 'STL',
    MetalType.ALUMINUM: 'ALU', 
    MetalType.MILD_STEEL: 'STL',
    MetalType.BRASS: 'BRS'
}

FORM_DETECTION_PATTERNS = {
    'sheet': ['sheet', 'plate', 'sheetmetal'],
    'bar': ['bar', 'rod', 'round'],
    'angle': ['angle', 'l-section'],
    'tube': ['tube', 'pipe', 'hollow']
}
```

## Phase 2: Implementation Strategy

### 2.1 AI Parsing Enhancement
Create `ItemCodeGenerator` class with methods:
- `parse_material_specs()` - Extract metal type, alloy, form from descriptions
- `standardize_dimensions()` - Convert various dimension formats to standard
- `generate_item_code()` - Create standardized code from parsed components
- `validate_item_code()` - Ensure code follows format rules

### 2.2 Database Changes
```python
# Add validation to Stock model
class Stock(models.Model):
    item_code = models.CharField(
        max_length=50,  # Increased from 255
        validators=[ItemCodeValidator()],
        help_text="Standardized item code (replaces Xero codes)"
    )

# Add helper fields to SupplierProduct
class SupplierProduct(models.Model):
    parsed_item_code = models.CharField(
        max_length=50,
        validators=[ItemCodeValidator()],
        help_text="Generated standardized item code"
    )
    item_code_confidence = models.DecimalField(
        max_digits=3, decimal_places=2,
        help_text="Confidence in generated item code"
    )
```

### 2.3 Conflict Resolution Strategy
1. **Existing Xero codes**: Map to new format where possible, maintain mapping table
2. **Duplicate materials**: Use sequence number to differentiate sources
3. **Ambiguous parsing**: Flag for manual review with confidence < 0.8

## Phase 3: Data Migration Plan

### 3.1 Migration Steps
1. **Analyze existing data**: Audit current `item_code` values in Stock
2. **Generate mapping table**: Old Xero codes → New standardized codes  
3. **Populate parsed_item_code**: Run AI parsing on all SupplierProduct records
4. **Validate mappings**: Manual review of low-confidence matches
5. **Update foreign keys**: Migrate any references to use new codes

### 3.2 Migration Script Structure
```python
class Command(BaseCommand):
    def handle(self):
        # Step 1: Create ItemCodeGenerator
        generator = ItemCodeGenerator()
        
        # Step 2: Process Stock items
        for stock in Stock.objects.all():
            new_code = generator.generate_from_stock(stock)
            migration_log.create(old_code=stock.item_code, new_code=new_code)
            
        # Step 3: Process SupplierProduct items  
        for product in SupplierProduct.objects.all():
            parsed_code = generator.generate_from_supplier_product(product)
            product.parsed_item_code = parsed_code
            product.save()
```

## Phase 4: Integration Points

### 4.1 Common Query Patterns
```python
# Find Stock by SupplierProduct
def find_stock_for_supplier_product(supplier_product):
    return Stock.objects.filter(
        item_code=supplier_product.parsed_item_code
    ).first()

# Find cheapest supplier for Stock item
def find_cheapest_supplier(stock_item):
    return SupplierProduct.objects.filter(
        parsed_item_code=stock_item.item_code
    ).order_by('variant_price').first()
```

### 4.2 Business Logic Updates
- **Purchase order creation**: Auto-suggest stock items based on supplier products
- **Cost comparison**: Compare supplier prices against current stock costs
- **Inventory matching**: Auto-match received stock to supplier products

## Phase 5: Quality Assurance

### 5.1 Validation Rules
- Item codes must be unique within each model
- Format validation via regex patterns
- Cross-reference validation between models
- Confidence thresholds for auto-assignment

### 5.2 Monitoring Dashboard
- Track parsing success rates
- Monitor duplicate/conflict resolution
- Alert on low-confidence mappings requiring review
- Report on cross-model matching statistics

## Risk Mitigation

### Technical Risks
- **AI parsing inconsistency**: Use ProductParsingMapping for deterministic results
- **Data loss**: Maintain complete audit trail of old→new code mappings
- **Performance**: Index new item_code fields, optimize queries

### Business Risks  
- **Disruption**: Phase rollout, maintain parallel systems during transition
- **User confusion**: Training on new code format, clear documentation
- **Integration breaks**: Comprehensive testing of Xero sync with new codes

## Success Metrics
- 95%+ parsing confidence rate for common materials
- <5% manual intervention required for code generation
- Sub-second query performance for cross-model lookups
- Zero data loss during migration
- Successful Xero integration with new code format

## Implementation Priority
1. **Phase 1**: Design and validate item code format
2. **Phase 2**: Build ItemCodeGenerator and validation system
3. **Phase 3**: Execute data migration with full audit trail
4. **Phase 4**: Implement cross-model integration points
5. **Phase 5**: Deploy monitoring and quality assurance tools

This plan creates a robust foundation for unified material identification across both internal inventory and supplier catalogs.