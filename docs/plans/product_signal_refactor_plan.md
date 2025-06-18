# Product Signal Refactor Plan

## Problem
The SupplierProduct signal is preventing bulk updates by triggering expensive LLM calls on every save(). This blocks operations like populating mapping_hash values for existing records.

## Solution
Remove the signal and manually call parsing logic only where needed.

## Steps

### 1. Research Signal Usage ✅ COMPLETED
Found all places where SupplierProduct records are created/updated:

**Key Creation Points (need manual parsing):**
- `apps/quoting/views.py` line 127-137: PDF upload via web interface
- `apps/quoting/scrapers/base.py` line 204-209: Web scraping 
- `scripts/import_supplier_products_one_off.py` line 162-166: CSV import
- `apps/job/management/commands/backport_data_restore.py`: Data restoration

**Update Operations (no parsing needed):**
- `apps/purchasing/views/product_mapping.py`: Validation updates parsed fields
- Migration scripts: Handle their own parsing
- Hash population command: Only updates hash field

### 2. Create Manual Functions ✅ COMPLETED
Created functions in `apps/quoting/services/product_parser.py`:

**A. create_mapping_record(instance):**
- Sets mapping_hash on SupplierProduct
- Creates empty ProductParsingMapping record with input fields
- No LLM calls

**B. populate_all_mappings_with_llm():**
- Finds all unpopulated ProductParsingMapping records
- Batch processes them with LLM
- Updates corresponding SupplierProduct parsed_* fields via backflow
- Operates on entire table, not individual products

### 3. Update Creation Points
**All record creation operations:**
- Call create_mapping_record() for each new product
- This creates empty ProductParsingMapping records

**After bulk operations (PDF upload, web scraping, CSV import):**
- Call populate_all_mappings_with_llm() once at the end
- This processes all unpopulated ProductParsingMapping records in batch

**Bulk operations that don't want LLM calls (hash population):**
- Only call create_mapping_record()

### 4. Remove Signal ✅ COMPLETED
Deleted the auto_parse_supplier_product signal from apps/quoting/signals.py and cleaned up unused imports.

### 5. Test ✅ COMPLETED
Verified:
- Bulk updates no longer trigger expensive LLM calls (populate_mapping_hashes completed 4,409 records in seconds)
- Manual function creation works correctly
- Existing functionality is preserved

### 6. Clean up Management Command ✅ COMPLETED
Deleted populate_mapping_hashes.py since bulk updates now work efficiently

## Benefits
- Bulk operations can create mapping records without expensive LLM calls
- LLM parsing happens immediately after record creation when desired
- More explicit control over when LLM parsing occurs
- Can populate mapping_hash efficiently for existing records
- Eliminates signal overhead
- Clear separation between record creation and LLM processing

## Files to Modify
- apps/quoting/signals.py (remove signal)
- apps/quoting/services/product_parser.py (add manual function)
- Any files that create SupplierProduct records (add manual calls)
- Delete apps/quoting/management/commands/populate_mapping_hashes.py