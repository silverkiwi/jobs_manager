/**
 * Purchase Order UI Management
 * 
 * Handles UI-related functions for the purchase order form
 */

import { renderMessages } from "./messages.js";
import { getState, getStatusDisplay } from "./purchase_order_state.js";

/**
 * Get the CSRF token from the page
 * @returns {string} CSRF token
 */
function getCsrfToken() {
  return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}

/**
 * Updates the submit button state based on autosave status and purchase order status
 */
export function updateSubmitButtonState() {
  const submitButton = document.getElementById("submit-purchase-order");
  if (!submitButton) return;

  const state = getState();
  const isDraft =
    !state.purchaseData.purchaseOrder ||
    !state.purchaseData.purchaseOrder.status ||
    state.purchaseData.purchaseOrder.status === "draft";

  if (isDraft && state.lastAutosaveSuccess) {
    submitButton.disabled = false;
    submitButton.title = "Submit purchase order to Xero";
  } else {
    submitButton.disabled = true;
    submitButton.title = isDraft
      ? "Please wait for changes to save before submitting"
      : "Only draft purchase orders can be submitted";
  }
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

  // If the status is not draft, make specific fields read-only
  if (
    state.purchaseData.purchaseOrder.status &&
    state.purchaseData.purchaseOrder.status !== "draft" &&
    state.purchaseData.purchaseOrder.status !== "deleted"
  ) {
    // Add a notice at the top of the form
    const formElement = document.getElementById("purchase-order-details-form");
    const noticeDiv = document.createElement("div");
    noticeDiv.className = "alert alert-info mb-3";
    noticeDiv.innerHTML = `<i class="bi bi-info-circle me-2"></i>This purchase order is in <strong>${getStatusDisplay(state.purchaseData.purchaseOrder.status)}</strong> status. Some fields cannot be edited.`;
    formElement.prepend(noticeDiv);

    // Make specific fields read-only (but not expected_delivery)
    const fieldsToLock = [
      "client_name",
      "client_id",
      "po_number",
      "order_date",
    ];
    fieldsToLock.forEach((fieldId) => {
      const field = document.getElementById(fieldId);
      if (field) {
        field.setAttribute("readonly", true);
        field.classList.add("form-control-plaintext");
        field.classList.remove("form-control");
      }
    });

    // Make the grid read-only
    window.setTimeout(() => {
      const state = getState();
      if (state.grid && state.grid.api) {
        state.grid.api.setGridOption("readOnly", true);
      }
    }, 500);
  }
}

/**
 * Block purchase order editing if status is DELETED
 */
export function blockPurchaseOrderEdition() {
  const formElement = document.getElementById("purchase-order-details-form");
  if (formElement) {
    const noticeDiv = document.createElement("div");
    noticeDiv.className = "alert alert-danger mb-3";
    noticeDiv.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i>This purchase order has been <strong>DELETED</strong>. No editing is allowed.`;
    formElement.prepend(noticeDiv);
  }

  const formInputs = [
    document.getElementById("client_name"), 
    document.getElementById("status"), 
    document.getElementById("expected_delivery"), 
    document.getElementById("reference")
  ];
  
  formInputs.forEach(input => {
    if (!input) return;
    
    input.setAttribute("disabled", true);
    
    if (input.classList.contains("form-control")) {
      input.classList.add("form-control-plaintext");
      input.classList.remove("form-control");
    } 
    
    if (input.classList.contains("form-select")) {
      input.classList.add("form-select-plaintext");
      input.classList.remove("form-select");
    }
  });

  const submitButton = document.getElementById("submit-purchase-order");
  if (submitButton) submitButton.style.display = "none";

  const gridDiv = document.querySelector("#purchase-order-lines-grid");
  if (gridDiv) {
    gridDiv.style.border = "2px solid #dc3545";
    gridDiv.style.backgroundColor = "rgba(220, 53, 69, 0.05)";
  }

  window.setTimeout(() => {
    const state = getState();
    if (state.grid && state.grid.api) {
      state.grid.api.setGridOption("readOnly", true);
      state.grid.api.setGridOption("editable", false);

      const columnDefs = state.grid.api.getColumnDefs();
      columnDefs.forEach((col) => {
        col.editable = false
      });
      state.grid.api.setGridOption("columnDefs", columnDefs);

      state.grid.api.refreshCells({ force: true });
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

  button.addEventListener("click", () => {
    fetch(`/purchases/purchase-orders/delete/${id}/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken()
      },
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(response.error);
        }
        return response.json();
      })
      .then(data => {
        if (!data.success) {
          throw new Error(data.error);
        }
        setTimeout(() => {
          window.location.href = "/purchases/purchase-orders/";
        }, 1000);
      })
      .catch(error => {
        renderMessages(
          [
            {
              "level": "danger",
              "message": error
            }
          ],
          "purchase-order")
      });
  });
}
