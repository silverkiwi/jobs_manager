/**
 * Purchase Order Form - Main Entry Point
 * 
 * Coordinates initialization of the purchase order form components
 */

import { initState, getState, updateState } from './purchase_order_state.js';
import { initializeGrid } from './purchase_order_grid.js';
import { fetchMetalTypes, updateMetalTypeValues } from './purchase_order_metal_types.js';
import {
  populateFormWithPurchaseOrderData,
  blockPurchaseOrderEdition,
  addLocalDeleteButton
} from './purchase_order_ui.js';
import { setupEventListeners } from './purchase_order_events.js';
import { updateJobSummary } from './purchase_order_summary.js';
import { initializeClientLookup } from './client_lookup.js';

/**
 * Initialize the application
 */
function initializeApp() {
  console.log("Initializing purchase order application");
  
  // Initialize state
  initState();
  
  // Load data from HTML elements
  loadDataFromDOM();
  
  // Fetch metal types from the server
  fetchMetalTypes()
    .then(metalTypes => {
      const state = getState();
      if (state.grid && state.grid.api) {
        updateMetalTypeValues(metalTypes);
      }
    });
  
  // Initialize the grid
  initializeGrid()
    .then(initialized => {
      if (initialized) {
        const state = getState();
        // Apply status-specific behavior
        if (state.purchaseData.purchaseOrder.status === "deleted") {
          blockPurchaseOrderEdition();
          // Note: addLocalRestoreButton is now called inside blockPurchaseOrderEdition
        }
        
        if (state.purchaseData.purchaseOrder.status === "draft") {
          addLocalDeleteButton(state.purchaseData.purchaseOrder.id);
        }
      }
    })
    .catch(error => {
      console.error("Failed to initialize grid:", error);
    });
  
  // Populate form with purchase order data
  populateFormWithPurchaseOrderData();
  
  // Initialize job summary section
  updateJobSummary();
  
  // Set up event listeners
  setupEventListeners();

  // Initialize client lookup functionality
  initializeClientLookup();
}

/**
 * Load data from DOM elements
 */
function loadDataFromDOM() {
  // Parse JSON data from HTML elements
  const jobsDataElement = document.getElementById("jobs-data");
  const lineItemsDataElement = document.getElementById("line-items-data");
  const purchaseOrderDataElement = document.getElementById("purchase-order-data");

  // Store data in the state
  updateState({
    purchaseData: {
      jobs: jobsDataElement ? JSON.parse(jobsDataElement.textContent) : [],
      lineItems: lineItemsDataElement ? JSON.parse(lineItemsDataElement.textContent) : [],
      purchaseOrder: purchaseOrderDataElement ? JSON.parse(purchaseOrderDataElement.textContent) : {},
    }
  });
  
  console.log("Purchase order data loaded:", getState().purchaseData);
}

// Initialize the application when the DOM is loaded
document.addEventListener("DOMContentLoaded", initializeApp);