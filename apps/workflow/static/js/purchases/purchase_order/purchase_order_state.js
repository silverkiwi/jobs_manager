/**
 * Purchase Order State Management
 * 
 * Central state management for the purchase order form
 */

// Initial state
const initialState = {
  grid: null,
  purchaseData: {
    jobs: [],
    lineItems: [],
    purchaseOrder: {},
  },
  lastAutosaveSuccess: true, // Default to true since data is already saved when loading
  metalTypeValues: ["unspecified"], // Default value
  isReadOnly: false, // Default to not read-only, since all new POs are editable
};

// Current state (private)
let state = { ...initialState };

/**
 * Initialize state to default values
 */
export function initState() {
  state = { ...initialState };
  
  // For backwards compatibility
  window.purchaseData = state.purchaseData;
}

/**
 * Get current state
 * @returns {Object} Current state
 */
export function getState() {
  return state;
}

/**
 * Update state with new values
 * @param {Object} newState - State updates
 */
export function updateState(newState) {
  state = { ...state, ...newState };
  
  // Keep window.purchaseData in sync for backward compatibility
  if (newState.purchaseData) {
    window.purchaseData = state.purchaseData;
  }
  
  // Keep window.grid in sync for backward compatibility
  if (newState.grid) {
    window.grid = state.grid;
  }
}

/**
 * Status display mapping
 */
export const STATUS_DISPLAY_MAP = {
  draft: "Draft",
  submitted: "Submitted to Supplier",
  partially_received: "Partially Received",
  fully_received: "Fully Received",
  deleted: "Deleted",
};

/**
 * Get status display name from status code
 * @param {string} status - Status code
 * @returns {string} Display name
 */
export function getStatusDisplay(status) {
  return STATUS_DISPLAY_MAP[status] || status;
}
