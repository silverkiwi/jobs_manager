/**
 * Purchase Order Metal Types Management
 * 
 * Handles fetching and updating metal type values
 */

import { fetchEnumChoices } from "../../enum-utils.js";
import { getState, updateState } from "./purchase_order_state.js";

/**
 * Fetch metal type values from the server
 * @returns {Promise} Promise resolving with metal type values
 */
export function fetchMetalTypes() {
  return fetchEnumChoices("MetalType")
    .then(choices => {
      const metalTypeValues = choices.map(choice => choice.value);
      console.log("Fetched metal type values:", metalTypeValues);
      
      // Update state with new values
      updateState({ metalTypeValues });
      
      return metalTypeValues;
    })
    .catch(error => {
      console.error("Error fetching metal type values:", error);
      return getState().metalTypeValues; // Return default values if API fails
    });
}

/**
 * Update metal type values in the grid
 * @param {Array} values - Metal type values
 */
export function updateMetalTypeValues(values) {
  const state = getState();
  if (!state.grid || !state.grid.api) {
    console.error("Grid not initialized, cannot update metal type values");
    return;
  }
  
  try {
    const column = state.grid.api.getColumnDef("metal_type");
    column.cellEditorParams.values = values;
    console.log("Updated metal type values in grid:", values);
  } catch (error) {
    console.error("Failed to update metal type values:", error);
  }
}
