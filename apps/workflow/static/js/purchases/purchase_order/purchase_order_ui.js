/**
 * Purchase Order UI Management
 * 
 * Handles UI-related functions for the purchase order form
 */

import { renderMessages } from "./messages.js";
import { getState, updateState, getStatusDisplay } from "./purchase_order_state.js";
import { updateGridEditability } from "./purchase_order_grid.js";

/**
 * Get the CSRF token from the page
 * @returns {string} CSRF token
 */
function getCsrfToken() {
  return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}

/**
 * Populate form with purchase order data
 */
export function populateFormWithPurchaseOrderData() {
  const state = getState();
  
  if (!state.purchaseData.purchaseOrder || !state.purchaseData.purchaseOrder.id) {
    // Set today's date for order date for new purchase orders
    const today = new Date();
    const formattedDate = today.toISOString().split("T")[0]; // Format as YYYY-MM-DD
    document.getElementById("order_date").value = formattedDate;
    return;
  }

  // Set the purchase order ID
  document.getElementById("purchase_order_id").value = state.purchaseData.purchaseOrder.id;

  // Set the PO number
  if (state.purchaseData.purchaseOrder.po_number) {
    document.getElementById("po_number").value = state.purchaseData.purchaseOrder.po_number;
  }

  // Set the supplier
  if (state.purchaseData.purchaseOrder.supplier) {
    document.getElementById("client_id").value = state.purchaseData.purchaseOrder.supplier;
    document.getElementById("client_name").value = state.purchaseData.purchaseOrder.supplier_name;
    
    // Set the supplier Xero ID if available
    if (state.purchaseData.purchaseOrder.client_xero_id) {
      document.getElementById("client_xero_id").value = state.purchaseData.purchaseOrder.client_xero_id;
    }
  }

  // Set the dates
  if (state.purchaseData.purchaseOrder.order_date) {
    document.getElementById("order_date").value = 
      state.purchaseData.purchaseOrder.order_date.split("T")[0];
  }

  if (state.purchaseData.purchaseOrder.expected_delivery) {
    document.getElementById("expected_delivery").value = 
      state.purchaseData.purchaseOrder.expected_delivery.split("T")[0];
  }

  if (state.purchaseData.purchaseOrder.status) {
    document.getElementById("status").value = state.purchaseData.purchaseOrder.status;
  }

  if (state.purchaseData.purchaseOrder.reference) {
    document.getElementById("reference").value = state.purchaseData.purchaseOrder.reference;
  }

  // If the status is not draft, make supplier field read-only with prominent notice
  if (
    state.purchaseData.purchaseOrder.status &&
    state.purchaseData.purchaseOrder.status !== "draft" &&
    state.purchaseData.purchaseOrder.status !== "deleted"
  ) {
    // Add prominent warning notice at the top of the form
    // Check if a notice already exists to prevent duplicates
    const container = document.querySelector(".container-fluid");
    const existingNotice = container.querySelector(".alert.alert-warning.po-status-notice");
    if (!existingNotice && container) {
      const noticeDiv = document.createElement("div");
      noticeDiv.className = "alert alert-warning mb-3 po-status-notice";
      noticeDiv.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i>This purchase order is in <strong>${getStatusDisplay(state.purchaseData.purchaseOrder.status)}</strong> status. Most fields cannot be changed.`;
      // Insert after the first row (title and back button) but before the form
      container.insertBefore(noticeDiv, container.children[1]);
    }
    
    // Add additional notice in the line items section
    const lineItemsSection = document.querySelector("#purchase-order-lines-section");
    const existingLineItemsNotice = lineItemsSection?.querySelector(".alert.alert-warning.line-items-notice");
    if (!existingLineItemsNotice && lineItemsSection) {
      const lineItemsNoticeDiv = document.createElement("div");
      lineItemsNoticeDiv.className = "alert alert-warning mb-3 line-items-notice";
      lineItemsNoticeDiv.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i>Line items cannot be changed after the purchase order is submitted.`;
      lineItemsSection.insertBefore(lineItemsNoticeDiv, lineItemsSection.firstChild);
    }

    // Make supplier name field readonly with visual cues
    const clientNameField = document.getElementById("client_name");
    if (clientNameField) {
      clientNameField.setAttribute("readonly", true);
      clientNameField.classList.add("form-control-plaintext");
      clientNameField.classList.remove("form-control");
      clientNameField.style.backgroundColor = "#f8f9fa";
      clientNameField.style.borderLeft = "3px solid #ffc107";
    }

    // Set the grid to read-only using our unified method
    window.setTimeout(() => {
      // Make sure the grid is initialized before trying to update it
      if (state.grid && state.grid.api) {
        // Update state to set the grid read-only
        updateState({ isReadOnly: true });
        
        // Use the unified method to update grid editability
        updateGridEditability();
      } else {
        console.warn("Grid not yet initialized, will retry setting readonly state");
        // Try again in a moment if the grid isn't ready
        setTimeout(() => {
          const updatedState = getState();
          if (updatedState.grid && updatedState.grid.api) {
            updateState({ isReadOnly: true });
            updateGridEditability();
          } else {
            console.error("Grid initialization timeout - could not set readonly state");
          }
        }, 1000);
      }
    }, 500);
  }
}

/**
 * Block purchase order editing if status is DELETED
 */
export function blockPurchaseOrderEdition() {
  const state = getState();
  const formElement = document.getElementById("purchase-order-details-form");
  
  if (formElement) {
    // Check if a notice already exists to prevent duplicates
    const existingNotice = formElement.querySelector(".alert.alert-danger");
    if (!existingNotice) {
      const noticeDiv = document.createElement("div");
      noticeDiv.className = "alert alert-danger mb-3 deleted-po-notice";
      noticeDiv.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i>This purchase order has been <strong>DELETED</strong>. To restore it, change the status dropdown back to "Draft" and save.`;
      formElement.prepend(noticeDiv);
    }
  }
  
  // Add additional notice in the line items section
  const lineItemsSection = document.querySelector("#purchase-order-lines-section");
  const existingLineItemsNotice = lineItemsSection?.querySelector(".alert.alert-danger.line-items-notice");
  if (!existingLineItemsNotice && lineItemsSection) {
    const lineItemsNoticeDiv = document.createElement("div");
    lineItemsNoticeDiv.className = "alert alert-danger mb-3 line-items-notice deleted-po-notice";
    lineItemsNoticeDiv.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i>Line items cannot be changed for deleted purchase orders.`;
    lineItemsSection.insertBefore(lineItemsNoticeDiv, lineItemsSection.firstChild);
  }

  // Get all form inputs except status field
  const formInputs = [
    document.getElementById("client_name"), 
    document.getElementById("expected_delivery"), 
    document.getElementById("reference")
  ];
  
  // Disable all inputs except status
  formInputs.forEach(input => {
    if (!input) return;
    
    input.setAttribute("disabled", true);
    
    if (input.classList.contains("form-control")) {
      input.classList.add("form-control-plaintext");
      input.classList.remove("form-control");
    }
  });
  
  // Get the status dropdown specifically
  const statusDropdown = document.getElementById("status");
  if (statusDropdown) {
    // Keep it enabled but add visual cue
    statusDropdown.style.borderColor = "#ffc107";
    statusDropdown.style.boxShadow = "0 0 0 0.25rem rgba(255, 193, 7, 0.25)";
    statusDropdown.title = "You can change the status back to Draft to restore this purchase order";
    
    // Add a highlight to make it obvious this is actionable
    statusDropdown.classList.add("border-warning");
  }

  // Make submit button visible for restoring via status change
  const submitButton = document.getElementById("submit-purchase-order");
  if (submitButton) {
    submitButton.textContent = "Update Status";
    submitButton.classList.remove("btn-primary");
    submitButton.classList.add("btn-warning");
    submitButton.title = "Change status to restore this purchase order";
  }

  const gridDiv = document.querySelector("#purchase-order-lines-grid");
  if (gridDiv) {
    gridDiv.style.border = "2px solid #dc3545";
    gridDiv.style.backgroundColor = "rgba(220, 53, 69, 0.05)";
  }

  // Use our unified approach to set grid as read-only
  window.setTimeout(() => {
    // Make sure the grid is initialized before trying to update it
    if (state.grid && state.grid.api) {
      updateState({ isReadOnly: true });
      updateGridEditability();
    } else {
      console.warn("Grid not yet initialized, will retry setting readonly state");
      // Try again in a moment if the grid isn't ready
      setTimeout(() => {
        const updatedState = getState();
        if (updatedState.grid && updatedState.grid.api) {
          updateState({ isReadOnly: true });
          updateGridEditability();
        } else {
          console.error("Grid initialization timeout - could not set readonly state");
        }
      }, 1000);
    }
  }, 500);

  document.body.classList.add("deleted-purchase-order");
}

/**
 * Add local delete button to the form
 * @param {string} id - Purchase order ID
 */
export function addLocalDeleteButton(id) {
  const button = document.getElementById("deletePOButton");
  if (!button) return;

  button.classList.remove("d-none");

  // Remove any existing event listeners to prevent duplicates
  const newButton = button.cloneNode(true);
  if (button.parentNode) {
    button.parentNode.replaceChild(newButton, button);
  }

  newButton.addEventListener("click", () => {
    fetch(`/purchasing/purchase-orders/${id}/delete/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken()
      },
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(response.error || "Failed to delete purchase order");
        }
        return response.json();
      })
      .then(data => {
        if (!data.success) {
          throw new Error(data.error || "Failed to delete purchase order");
        }
        
        renderMessages(
          [
            {
              "level": "success",
              "message": "Purchase order deleted successfully"
            }
          ],
          "purchase-order"
        );
        
        setTimeout(() => {
          window.location.href = "/purchases/purchase-orders/";
        }, 1000);
      })
      .catch(error => {
        renderMessages(
          [
            {
              "level": "danger",
              "message": error.message || "An error occurred while deleting the purchase order"
            }
          ],
          "purchase-order"
        );
      });
  });
}