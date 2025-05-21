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
  const purchaseOrderId = getPurchaseOrderId();

  // Add event listener for the "Add Item" button
  const addButton = document.getElementById('add-line-item');
  if (addButton) {
    addButton.addEventListener('click', function () {
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
    input.addEventListener("change", function () {
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

  const printButton = document.getElementById("printPO");
  if (printButton) {
    printButton.addEventListener("click", async () => {
      try {
        if (!purchaseOrderId) {
          throw new Error('Purchase Order ID not found');
        }

        const response = await fetch(`/api/purchase-orders/${purchaseOrderId}/pdf`);

        if (!response.ok) {
          throw new Error('Failed to generate Purchase Order PDF');
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const pdfWindow = window.open(url, "_blank");

        if (!pdfWindow) {
          throw new Error('Popup blocked. Please allow popups to print the purchase order');
        }

        pdfWindow.print();
      } catch (error) {
        console.error('Print error:', error);
        renderMessages([
          {
            level: "error",
            message: `Unable to print: ${error.message}`
          }
        ], "toast-container");
      }
    });
  }

  const emailButton = document.getElementById("emailPO");
  if (emailButton) {
    emailButton.addEventListener("click", async () => {
      try {
        const endpoint = `/api/purchase-orders/${purchaseOrderId}/email/`;
        const response = await fetch(endpoint, {
          method: "POST",
          headers: {
            "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
            "Content-Type": "application/json"
          }
        });
        const data = await response.json();

        if (!data.success) {
          throw new Error(`Error sending e-mail: ${data.error || 'contact the admin!'}`);
        }

        if (!data.mailto_url) {
          throw new Error(`Error sending e-mail: ${data.error || 'contact the admin!'}`);
        }

        // If no PDF, then we can just open the e-mail directly
        if (!data.pdf_content) {
          window.open(data.mailto_url, "_blank");
          return;
        }

        const pdfBlob = new Blob(
          [Uint8Array.from(atob(data.pdf_content), c => c.charCodeAt(0))],
          { type: 'application/pdf' }
        );

        const pdfUrl = URL.createObjectURL(pdfBlob);
        const downloadLink = document.createElement("a");

        downloadLink.href = pdfUrl;
        downloadLink.download = data.pdf_name;

        document.body.appendChild(downloadLink);

        downloadLink.click();

        document.body.removeChild(downloadLink);

        const enhancedBody = decodeURIComponent(data.body) + "\n\n--- \n***⚠️Note for MSM Staff⚠️***: Please attach the Purchase Order PDF file that was just downloaded."

        const emailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${data.email}&su=${encodeURIComponent(data.subject)}&body=${encodeURIComponent(enhancedBody)}`;
        window.open(emailUrl, "_blank");
      } catch (error) {
        console.error('Print error:', error);
        renderMessages([
          {
            level: "error",
            message: `Unable to print: ${error}`
          }
        ], "toast-container");
      }
    });
  }

  // Add event listener for the delete Xero PO button
  const deleteButton = document.getElementById("deleteXeroPOButton");
  if (deleteButton) {
    deleteButton.addEventListener("click", () => {
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
          "toast-container"
        );
      }
    });
  }
}

/**
 * Gets the PO ID based on the input element present in the template.
 * 
 * @returns {String | null} The purchase order ID based on the input value, or null if the element is not found or if the value is blank.
 */
function getPurchaseOrderId() {
  const purchaseOrderIdInput = document.getElementById("purchase_order_id");

  if (!purchaseOrderIdInput) {
    return null;
  }

  return purchaseOrderIdInput.value !== '' ? purchaseOrderIdInput.value : null;
}
