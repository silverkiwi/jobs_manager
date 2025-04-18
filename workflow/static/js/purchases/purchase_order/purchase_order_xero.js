/**
 * Purchase Order Xero Integration
 * 
 * Handles Xero integration for purchase orders
 */

import { renderMessages } from "./messages.js";
import { getState, updateState } from "./purchase_order_state.js";
import { collectPurchaseOrderData, saveDataToServer } from "./purchase_order_autosave.js";
import { updateSubmitButtonState } from "./purchase_order_ui.js";

/**
 * Get the CSRF token from the page
 * @returns {string} CSRF token
 */
function getCsrfToken() {
  return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}

/**
 * Submits the purchase order to Xero
 */
export function submitPurchaseOrderToXero() {
  // Get the purchase order ID
  const purchaseOrderId = document.getElementById("purchase_order_id").value;

  // Show loading state
  const submitButton = document.getElementById("submit-purchase-order");
  const originalText = submitButton.innerHTML;
  submitButton.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Submitting...';
  submitButton.disabled = true;

  // If we don't have a purchase order ID yet, we need to save the form first
  if (!purchaseOrderId) {
    // Collect the form data
    const formData = collectPurchaseOrderData();

    // Save the form data
    saveDataToServer(formData)
      .then((response) => {
        if (response && response.po_number) {
          // Now we have a purchase order ID, so we can submit to Xero
          const newPurchaseOrderId = document.getElementById("purchase_order_id").value;
          if (newPurchaseOrderId) {
            // Submit to Xero with the new ID
            submitToXero(newPurchaseOrderId, submitButton, originalText);
          } else {
            // Still no ID, show error
            renderMessages(
              [
                {
                  level: "error",
                  message: "Could not create purchase order. Please try again.",
                },
              ],
              "purchase-order-messages",
            );

            // Reset button and update state
            submitButton.innerHTML = originalText;
            updateState({ lastAutosaveSuccess: false });
            updateSubmitButtonState();
          }
        } else {
          // Error saving
          renderMessages(
            [
              {
                level: "error",
                message: "Could not create purchase order. Please try again.",
              },
            ],
            "purchase-order-messages",
          );

          // Reset button and update state
          submitButton.innerHTML = originalText;
          updateState({ lastAutosaveSuccess: false });
          updateSubmitButtonState();
        }
      })
      .catch((error) => {
        console.error("Error saving purchase order:", error);

        // Show error message
        renderMessages(
          [
            {
              level: "error",
              message: `Error saving purchase order: ${error.message}`,
            },
          ],
          "purchase-order-messages",
        );

        // Reset button and update state
        submitButton.innerHTML = originalText;
        updateState({ lastAutosaveSuccess: false });
        updateSubmitButtonState();
      });
  } else {
    // We already have a purchase order ID, so we can submit to Xero directly
    submitToXero(purchaseOrderId, submitButton, originalText);
  }
}

/**
 * Submit the purchase order to Xero
 * @param {string} purchaseOrderId - Purchase order ID
 * @param {HTMLElement} submitButton - Submit button element
 * @param {string} originalText - Original button text
 */
function submitToXero(purchaseOrderId, submitButton, originalText) {
  // Submit to Xero
  fetch(`/api/xero/purchase-order/${purchaseOrderId}/create/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Server responded with status ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        // Show success message
        renderMessages(
          data.messages || [
            {
              level: "success",
              message: "Purchase order submitted to Xero successfully.",
            },
          ],
          "purchase-order-messages",
        );

        // Hide the submit button
        submitButton.style.display = "none";

        // Reload the page after a short delay
        setTimeout(() => {
          window.location.reload();
        }, 2000);
      } else {
        // Show error message
        renderMessages(
          data.messages || [
            {
              level: "error",
              message: data.error || "Failed to submit purchase order to Xero.",
            },
          ],
          "purchase-order-messages",
        );

        // Reset button and update state
        submitButton.innerHTML = originalText;
        updateState({ lastAutosaveSuccess: false });
        updateSubmitButtonState();
      }
    })
    .catch((error) => {
      console.error("Error submitting purchase order to Xero:", error);

      // Show error message
      renderMessages(
        [
          {
            level: "error",
            message: `Error submitting purchase order to Xero: ${error.message}`,
          },
        ],
        "purchase-order-messages",
      );

      // Reset button and update state
      submitButton.innerHTML = originalText;
      updateState({ lastAutosaveSuccess: false });
      updateSubmitButtonState();
    });
}