/**
 * Supplier Quote Data Handler
 *
 * This module handles pre-filling the purchase order form with data extracted from a supplier quote.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if supplier quote data is present
    const supplierQuoteDataElement = document.getElementById('supplier-quote-data');
    if (!supplierQuoteDataElement) {
        return; // No supplier quote data, nothing to do
    }
    
    try {
        // Parse the supplier quote data
        const supplierQuoteData = JSON.parse(supplierQuoteDataElement.textContent);
        console.log('Supplier quote data:', supplierQuoteData);
        
        // TODO: Implement form pre-filling using the supplier quote data
        // This will be implemented in a future update
        
    } catch (error) {
        console.error('Error processing supplier quote data:', error);
    }
});

document.addEventListener('DOMContentLoaded', function() {
    // Check if supplier quote data is present
    const supplierQuoteDataElement = document.getElementById('supplier-quote-data');
    if (!supplierQuoteDataElement) {
        return; // No supplier quote data, nothing to do
    }
    
    try {
        // Parse the supplier quote data
        const supplierQuoteData = JSON.parse(supplierQuoteDataElement.textContent);
        if (!supplierQuoteData || Object.keys(supplierQuoteData).length === 0) {
            return; // Empty data, nothing to do
        }
        
        console.log('Supplier quote data loaded:', supplierQuoteData);
        
        // Pre-fill the supplier field if available
        if (supplierQuoteData.supplier && supplierQuoteData.supplier.name) {
            const supplierName = supplierQuoteData.supplier.name;
            
            // Set the supplier name in the input field
            const clientNameInput = document.getElementById('client_name');
            if (clientNameInput) {
                clientNameInput.value = supplierName;
                
                // Trigger the search to find the supplier
                const event = new Event('input', { bubbles: true });
                clientNameInput.dispatchEvent(event);
            }
        }
        
        // Set reference if available
        if (supplierQuoteData.quote_reference) {
            const referenceInput = document.getElementById('reference');
            if (referenceInput) {
                referenceInput.value = supplierQuoteData.quote_reference;
                
                // Trigger change event to update any dependent fields
                const event = new Event('change', { bubbles: true });
                referenceInput.dispatchEvent(event);
            }
        }
        
        // Pre-fill line items if available
        if (supplierQuoteData.items && supplierQuoteData.items.length > 0 && window.grid && window.grid.api) {
            // Clear existing rows except the last empty one
            const rowsToRemove = [];
            window.grid.api.forEachNode((node, index) => {
                if (index < window.grid.api.getDisplayedRowCount() - 1) {
                    rowsToRemove.push(node.data);
                }
            });
            
            if (rowsToRemove.length > 0) {
                window.grid.api.applyTransaction({ remove: rowsToRemove });
            }
            
            // Add the supplier quote items
            const rowsToAdd = supplierQuoteData.items.map(item => {
                return {
                    job: "", // No job assigned yet
                    description: item.description || "",
                    quantity: item.quantity || 1,
                    unit_cost: item.unit_price || null,
                    price_tbc: item.unit_price === null || item.unit_price === undefined,
                    metal_type: item.metal_type || "unspecified",
                    alloy: item.alloy || "",
                    specifics: item.specifics || ""
                };
            });
            
            window.grid.api.applyTransaction({ add: rowsToAdd });
            
            // Adjust grid height
            if (typeof adjustGridHeight === 'function') {
                adjustGridHeight();
            }
        }
        
    } catch (error) {
        console.error('Error processing supplier quote data:', error);
    }
});