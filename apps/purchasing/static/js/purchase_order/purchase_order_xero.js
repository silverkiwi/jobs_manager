/**
 * Purchase Order Xero Integration
 *
 * Handles Xero integration for purchase orders
 */

import { renderMessages } from "./messages.js";
import { getState, updateState } from "./purchase_order_state.js";
import {
  collectPurchaseOrderData,
  saveDataToServer,
} from "./purchase_order_autosave.js";

/**
 * Get the CSRF token from the page
 * @returns {string} CSRF token
 */
function getCsrfToken() {
  return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}
