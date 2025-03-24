/**
 * Purchase Order Autosave
 * 
 * Handles automatic saving of purchase order data as changes are made.
 * Uses debouncing to prevent excessive server requests.
 * Follows the same pattern as timesheet autosave for consistency.
 */

import { renderMessages } from "./messages.js";

let deletedLineItems = [];

/**
 * Marks a line item as deleted for synchronization purposes.
 * This handles AG Grid's deleted rows separately from the form,
 * ensuring the backend correctly processes grid-level changes.
 */
export function markLineItemAsDeleted(lineItemId) {
  if (lineItemId) {
    console.log("Adding line item to deletion list:", lineItemId);
    deletedLineItems.push(lineItemId);
    console.log("Current deletion list:", deletedLineItems);
  }
}

/**
 * Creates a debounced version of a function that delays its execution until after a period of inactivity.
 *
 * @param {Function} func - The function to debounce
 * @param {number} wait - The number of milliseconds to wait before executing the function
 * @returns {Function} A debounced version of the input function
 */
function debounce(func, wait) {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

/**
 * Collects all data from the purchase order form and grid
 * @returns {Object} Object containing purchase order and line item data
 */
function collectPurchaseOrderData() {
  console.log('Collecting purchase order data for autosave');
  
  // Get basic form data
  const clientIdEl = document.getElementById('client_id');
  const expectedDeliveryEl = document.getElementById('expected_delivery');
  
  const purchaseOrderData = {
    client_id: clientIdEl ? clientIdEl.value : null,
    expected_delivery: expectedDeliveryEl ? expectedDeliveryEl.value : null,
  };
  
  // Collect line items from the grid
  const lineItems = [];
  if (window.grid) {
    window.grid.forEachNode(node => {
      // Only include rows that have some data
      if (node.data.job || node.data.description || 
          node.data.quantity > 0 || node.data.unit_cost !== '') {
        lineItems.push({...node.data});
      }
    });
  }
  
  return {
    purchase_order: purchaseOrderData,
    line_items: lineItems,
    deleted_line_items: deletedLineItems
  };
}

/**
 * Main autosave function that collects data and sends it to the server
 */
function autosaveData() {
  console.log('Autosaving purchase order data');
  const collectedData = collectPurchaseOrderData();
  
  // Filter out incomplete line items
  collectedData.line_items = collectedData.line_items.filter(
    item => item.job && item.description
  );
  
  // Changed validation - proceed if either we have entries to update or delete
  if (
    collectedData.line_items.length === 0 &&
    collectedData.deleted_line_items.length === 0
  ) {
    console.log("No data to save - no line items or deletions");
    return;
  }
  
  console.log("Saving data:", {
    lineItems: collectedData.line_items.length,
    deletedLineItems: collectedData.deleted_line_items.length,
  });
  
  saveDataToServer(collectedData);
}

/**
 * Saves the collected data to the server via AJAX
 * @param {Object} collectedData The data to save
 */
function saveDataToServer(collectedData) {
  console.log("Autosaving purchase order data to /api/autosave-purchase-order/...", {
    line_items: collectedData.line_items.length,
    deleted_line_items: collectedData.deleted_line_items.length,
  });
  
  fetch('/api/autosave-purchase-order/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify(collectedData)
  })
  .then(response => {
    if (!response.ok) {
      console.error("Server responded with an error:", response.status);
      return response.json().then(data => {
        console.error("Error details:", data);
        throw new Error(data.error || "Server error");
      });
    }
    console.log("Autosave successful");
    deletedLineItems = [];
    return response.json();
  })
  .then(data => {
    // If this was a new PO and we got back a PO number, update the field
    if (data.po_number && document.getElementById('po_number')) {
      document.getElementById('po_number').value = data.po_number;
    }
    
    // Display messages
    renderMessages(data.messages || [], "purchase-order-messages");
    
    console.log("Autosave successful:", data);
  })
  .catch(error => {
    console.error("Autosave failed:", error);
    renderMessages([{
      level: "error",
      message: `Failed to save: ${error.message}`
    }], "purchase-order-messages");
  });
}

/**
 * Get the CSRF token from the page
 * @returns {string} The CSRF token
 */
function getCsrfToken() {
  return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}

// Debounced version of autosave
export const debouncedAutosave = debounce(autosaveData, 1500);

// Make debouncedAutosave available globally
window.debouncedAutosave = debouncedAutosave;

// Export for use in modules
export default debouncedAutosave;