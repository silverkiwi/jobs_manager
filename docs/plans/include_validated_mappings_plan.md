# Product Mapping Validation Filter Fix Plan

## Problem Analysis

The product mapping validation page has several issues:

1. **View Logic Issue** (`apps/purchasing/views/product_mapping.py:13-56`): The view only shows unvalidated mappings in the main list, but the filter expects to show all mappings and filter them client-side.

2. **Template Structure Issue** (`product_mapping_validation.html:71`): The template only loops through `unvalidated_mappings`, so validated mappings are never rendered to the DOM for filtering.

3. **JavaScript Location Issue** (`product_mapping_validation.html:227-342`): JavaScript is embedded in the HTML template instead of being in a separate file.

4. **Filter Logic Issue**: The filter should default to "unvalidated" but needs all mappings available in the DOM to function properly.

## Solution Plan

### 1. Fix View Logic ✅ COMPLETED
- ✅ Modified `product_mapping_validation` view to return all mappings (both validated and unvalidated) as a single list
- ✅ Combined the two separate querysets into one comprehensive list ordered appropriately
- ✅ Maintained the stats calculations
- ✅ Passed all mappings to template as `all_mappings` context variable

### 2. Update Template Structure ✅ COMPLETED
- ✅ Changed template to loop through all mappings instead of just unvalidated ones
- ✅ Rendered all mappings to DOM so JavaScript filtering can work on the full dataset
- ✅ Kept status filter defaulting to "unvalidated" as requested
- ✅ Updated context variable references

### 3. Extract JavaScript to Separate File ✅ COMPLETED
- ✅ Created `apps/purchasing/static/purchasing/js/product_mapping_validation.js`
- ✅ Moved all JavaScript from template to this new file
- ✅ Updated template to include the new JS file in the extra_js block
- ✅ Ensured proper separation of concerns

### 4. Fix Filter Behavior ✅ COMPLETED
- ✅ Kept status filter default as "unvalidated" (as user requested)
- ✅ JavaScript properly filters the full dataset on page load
- ✅ Updated filtering logic to work with all mappings being present in DOM

### 5. Files Modified/Created ✅ COMPLETED
- ✅ **Modified**: `apps/purchasing/views/product_mapping.py` - Updated view to return all mappings
- ✅ **Modified**: `apps/purchasing/templates/purchasing/product_mapping_validation.html` - Updated template structure, removed inline JS, added JS file reference
- ✅ **Created**: `apps/purchasing/static/purchasing/js/product_mapping_validation.js` - Extracted JavaScript functionality

## Implementation Summary

This plan has been **FULLY IMPLEMENTED** and ensures proper separation of concerns (HTML/CSS/JS in separate files) while fixing the core filtering functionality. The page now:

- Loads all mappings into the DOM (both validated and unvalidated)
- Defaults to showing only unvalidated items on page load
- Allows the filter to work properly to show validated items, all items, or any other filter combination
- Maintains proper code organization with separate JS files

The filtering system now works correctly with all mappings available in the DOM, allowing users to filter by status, metal type, Xero status, and search terms across the complete dataset.