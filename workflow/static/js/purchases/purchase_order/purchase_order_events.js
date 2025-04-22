/**
 * Purchase Order Event Handlers
 * 
 * Sets up event listeners for the purchase order form
 */

import { getState, updateState } from "./purchase_order_state.js";
import { createNewRowShortcut, updateGridEditability } from "./purchase_order_grid.js";
import { debouncedAutosave } from "./purchase_order_autosave.js";
import { deleteXeroPurchaseOrder } from "./purchase_order_xero_actions.js";
import { renderMessages } from "./messages.js";

/**
 * Set up event listeners for the purchase order form
 */
export function setupEventListeners() {
  // Add event listener for the "Add Item" button
  const addButton = document.getElementById('add-line-item');
  if (addButton) {
    addButton.addEventListener('click', function() {
      const state = getState();
      if (!state.grid || !state.grid.api) {
        console.error("Grid not initialized");
        return;
      }
      
      createNewRowShortcut(state.grid.api);
    });
  }
  
  // Add event listeners for all form fields with the autosave-input class
  const autosaveInputs = document.querySelectorAll(".autosave-input");
  autosaveInputs.forEach((input) => {
    input.addEventListener("change", function() {
      const state = getState();
      
      // Update our data model if this is the status field
      if (this.id === "status" && state.purchaseData.purchaseOrder) {
        const oldStatus = state.purchaseData.purchaseOrder.status;
        const newStatus = this.value;
        
        // Validate status change if moving from draft to another status
        if (oldStatus === "draft" && newStatus !== "draft") {
          // Check if supplier has a Xero ID
          const clientXeroIdInput = document.getElementById("client_xero_id");
          const hasXeroId = clientXeroIdInput && clientXeroIdInput.value;
          
          if (!hasXeroId) {
            // Prevent status change and show error message
            renderMessages(
              [
                {
                  level: "error",
                  message: "Cannot change status from Draft: Supplier must be found in Xero first. Please select or create a supplier.",
                },
              ],
              "purchase-order"
            );
            
            // Reset the dropdown to draft
            this.value = "draft";
            return;
          }
        }
        
        // Only process if status actually changed
        if (oldStatus !== newStatus) {
          // Clean up any existing UI elements
          document.querySelectorAll('.alert').forEach(notice => {
            notice.style.display = 'none';
          });
          
          // Reset all UI styles
          document.querySelectorAll('.form-control-plaintext, .border-warning').forEach(el => {
            el.classList.remove('form-control-plaintext', 'border-warning');
            if (el.tagName === 'INPUT') el.classList.add('form-control');
          });
          
          // Update state with new status
          updateState({
            purchaseData: {
              ...state.purchaseData,
              purchaseOrder: {
                ...state.purchaseData.purchaseOrder,
                status: newStatus
              }
            },
            isReadOnly: newStatus !== "draft"
          });
          
          // Just update grid editability - the form will be refreshed with the autosave
          updateGridEditability();
        }
      }
      
      debouncedAutosave().then((success) => {
        updateState({ lastAutosaveSuccess: success });
      });
    });
  });
  
  // Add event listener for the delete Xero PO button
  const deleteButton = document.getElementById("deleteXeroPOButton");
  if (deleteButton) {
    deleteButton.addEventListener("click", () => {
      const purchaseOrderIdInput = document.getElementById("purchase_order_id");
      const purchaseOrderId = purchaseOrderIdInput ? purchaseOrderIdInput.value : null;

      if (purchaseOrderId) {
        deleteXeroPurchaseOrder(purchaseOrderId);
      } else {
        console.error("Cannot delete Xero PO: Purchase Order ID not found in hidden input.");
        renderMessages(
          [
            {
              level: "error",
              message: "Cannot delete Xero PO: Purchase Order ID not found.",
            },
          ],
          "purchase-order-messages",
        );
      }
    });
  }
}
