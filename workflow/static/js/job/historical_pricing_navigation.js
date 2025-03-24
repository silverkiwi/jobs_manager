/**
 * Debug version of historical pricing navigation
 * Temporarily replace your current historical_pricing_navigation.js with this
 */

// State management for historical navigation
let currentHistoricalIndex = -1; // -1 means current data (not historical)
let historicalPricings = [];
let isViewingHistorical = false;
let originalGridState = null;
let localJobPricingHistory = []; // Use a local variable for backup

/**
 * Initialize the historical pricing navigation
 */
export function initHistoricalNavigation() {
  console.log("=== HISTORICAL NAVIGATION DEBUG ===");
  
  // Debug what data is available
  console.log("window.jobPricingHistory:", window.jobPricingHistory);
  console.log("window.historical_job_pricings_json:", window.historical_job_pricings_json);
  
  // Try to find historical data in various possible locations
  if (window.jobPricingHistory && Array.isArray(window.jobPricingHistory)) {
    localJobPricingHistory = window.jobPricingHistory;
    console.log(`Historical pricing records found: ${localJobPricingHistory.length}`);
    
    if (localJobPricingHistory.length > 0) {
      console.log(`First historical record sample:`, localJobPricingHistory[0]);
    }
  } 
  // Try alternative source if primary not found
  else if (window.historical_job_pricings_json && Array.isArray(window.historical_job_pricings_json)) {
    localJobPricingHistory = window.historical_job_pricings_json;
    window.jobPricingHistory = localJobPricingHistory; // Set it for consistency
    console.log(`Historical pricing records found in alternative source: ${localJobPricingHistory.length}`);
  }
  else {
    console.warn("No historical pricing data found in expected locations");
    localJobPricingHistory = []; // Default to empty
    window.jobPricingHistory = localJobPricingHistory; // Set it for consistency
  }
  
  // Only show navigation if we have historical data and job is special
  const jobStatus = document.getElementById('job_status')?.value;
  console.log("Current job status:", jobStatus);
  
  // Debug element existence
  ['historicalPricingNav', 'prevMonthBtn', 'nextMonthBtn', 'returnToCurrentBtn', 'currentHistoricalMonth'].forEach(id => {
    const element = document.getElementById(id);
    console.log(`Element #${id} exists:`, !!element);
  });
  
  if (localJobPricingHistory.length > 0 && jobStatus === 'special') {
    const nav = document.getElementById('historicalPricingNav');
    if (nav) {
      nav.classList.remove('d-none');
      console.log("Navigation controls are now visible");
    }
    
    // Add event listeners to buttons
    const prevBtn = document.getElementById('prevMonthBtn');
    if (prevBtn) {
      prevBtn.addEventListener('click', function() {
        console.log("Previous button clicked");
        navigateToPreviousMonth();
      });
    }
    
    const nextBtn = document.getElementById('nextMonthBtn');
    if (nextBtn) {
      nextBtn.addEventListener('click', function() {
        console.log("Next button clicked");
        navigateToNextMonth();
      });
    }
    
    const returnBtn = document.getElementById('returnToCurrentBtn');
    if (returnBtn) {
      returnBtn.addEventListener('click', function() {
        console.log("Return button clicked");
        returnToCurrent();
      });
    }
    
    // Initial button state
    updateNavigationButtons();
  } else {
    console.warn("Navigation not shown - either no historical data or not a special job");
  }
  
  // Call this in init
  // addDebugButton();
}

/**
 * Navigate to the previous month's historical data
 */
function navigateToPreviousMonth() {
  const historySource = window.jobPricingHistory || localJobPricingHistory;
  
  if (!historySource || historySource.length === 0) {
    console.log("No historical data available");
    return;
  }
  
  let newIndex = currentHistoricalIndex;
  
  if (newIndex === -1) {
    // If at current data, go to most recent historical
    newIndex = 0;
  } else if (newIndex < historySource.length - 1) {
    // Navigate one entry older
    newIndex++;
  }
  
  loadHistoricalData(newIndex);
}

/**
 * Navigate to the next month's historical data
 */
function navigateToNextMonth() {
  console.log("Navigating to next month");
  console.log("Current index:", currentHistoricalIndex);
  
  if (currentHistoricalIndex > 0) {
    currentHistoricalIndex--;
    console.log("New index:", currentHistoricalIndex);
    loadHistoricalData(currentHistoricalIndex);
    updateNavigationButtons();
  } else if (currentHistoricalIndex === 0) {
    console.log("At most recent record, returning to current data");
    returnToCurrent();
  } else {
    console.log("Already at current data");
  }
}

/**
 * Return to current (non-historical) data
 */
function returnToCurrent() {
  console.log("Returning to current data");
  
  // Force a page reload - most reliable way to reset everything
  window.location.reload();
}

/**
 * Update navigation button states based on current index
 */
function updateNavigationButtons() {
  console.log("Updating navigation buttons, current index:", currentHistoricalIndex);
  
  const prevBtn = document.getElementById('prevMonthBtn');
  const nextBtn = document.getElementById('nextMonthBtn');
  const monthDisplay = document.getElementById('currentHistoricalMonth');
  const returnBtn = document.getElementById('returnToCurrentBtn');
  
  if (!prevBtn || !nextBtn || !monthDisplay || !returnBtn) {
    console.error("One or more navigation elements not found!");
    return;
  }
  
  // Update button states
  prevBtn.disabled = currentHistoricalIndex >= localJobPricingHistory.length - 1;
  nextBtn.disabled = currentHistoricalIndex <= -1;
  returnBtn.classList.toggle('d-none', currentHistoricalIndex === -1);
  
  // Update date display
  if (currentHistoricalIndex === -1) {
    monthDisplay.innerHTML = 'Current Data';
    monthDisplay.title = 'Viewing current job data';
    console.log("Date display set to: Current Data");
  } else {
    const historicalData = localJobPricingHistory[currentHistoricalIndex];
    
    if (historicalData && historicalData.created_at) {
      const date = new Date(historicalData.created_at);
      
      // Format the date for display
      const formattedDate = date.toLocaleDateString('default', { 
        day: 'numeric', 
        month: 'long', 
        year: 'numeric' 
      });
      
      monthDisplay.innerHTML = `Data as of ${formattedDate}`;
      monthDisplay.title = `Historical data archived on ${formattedDate}`;
      console.log("Date display set to:", formattedDate);
    } else {
      monthDisplay.innerHTML = 'Historical Data (No Date)';
      monthDisplay.title = 'Historical data with no timestamp';
      console.log("Date display set to: Historical Data (No Date)");
    }
  }
}

/**
 * Load historical data for a specific index
 */
function loadHistoricalData(index) {
  console.log(`Loading historical data index: ${index}`);
  isViewingHistorical = (index !== -1);
  currentHistoricalIndex = index;
  
  // Insert this near the top of the function
  inspectAllGrids();
  
  // If returning to current view
  if (index === -1) {
    // Restore original grid state if we saved it
    if (originalGridState !== null) {
      console.log(`Restoring original grid state: ${originalGridState}`);
      
      // Get current toggle state
      const currentToggleState = document.getElementById('toggleGridButton').checked;
      
      // Only toggle if the state is different
      if (currentToggleState !== originalGridState) {
        console.log("Toggling grid back to original state");
        toggleGrid("historical");
      }
      
      originalGridState = null;
    }
    
    // Force reload from server
    console.log("Reloading current data from server");
    window.location.reload();
    return;
  }
  
  // CRITICAL FIX: Always use local variable, not window variable
  if (index >= localJobPricingHistory.length) {
    console.error(`Error: Historical data index ${index} out of bounds (max: ${localJobPricingHistory.length - 1})`);
    return;
  }
  
  const historicalData = localJobPricingHistory[index];
  
  if (!historicalData) {
    console.error(`Error: No historical data found at index ${index}`);
    return;
  }
  
  console.log("Successfully retrieved historical data:", historicalData);
  
  // Set visual indicator that we're in historical mode
  document.body.classList.add('viewing-historical-data');
  
  // Create or update the historical banner
  createHistoricalBanner(historicalData.created_at);
  
  // Show the date of the historical data in the navigation control
  if (historicalData.created_at) {
    setHistoricalDateDisplay(historicalData.created_at);
  }
  
  // Update all section types: reality, estimate, quote
  const sections = ['reality', 'estimate', 'quote'];
  
  // Update each section
  sections.forEach(section => {
    // Update time entries
    updateEntriesGrid(section, 'time', historicalData[`${section}_time_entries`] || []);
    
    // Update material entries
    updateEntriesGrid(section, 'material', historicalData[`${section}_material_entries`] || []);
    
    // Update adjustment entries
    updateEntriesGrid(section, 'adjustment', historicalData[`${section}_adjustment_entries`] || []);
  });
  
  // Update totals for all tables
  updateTotals(historicalData);
  
  // Ensure navigation buttons reflect correct state
  setTimeout(updateNavigationButtons, 100);

  // Add this at the end of your loadHistoricalData function
  setTimeout(() => {
    console.log("=== DELAYED GRID VERIFICATION (after 1 second) ===");
    console.log("Checking if grids have maintained historical data...");
    
    ['reality', 'estimate', 'quote'].forEach(section => {
      ['time', 'material', 'adjustment'].forEach(type => {
        const gridId = `${section}${capitalize(type)}Table`;
        if (window.grids && window.grids[gridId] && window.grids[gridId].api) {
          const api = window.grids[gridId].api;
          const currentRows = [];
          api.forEachNode(node => {
            currentRows.push(node.data);
          });
          console.log(`DELAYED CHECK: ${gridId} has ${currentRows.length} rows`);
          
          // Get the expected historical data
          const keyToCheck = `${section}_${type}_entries`;
          const expectedEntries = historicalData[keyToCheck] || [];
          console.log(`DELAYED CHECK: Expected ${expectedEntries.length} rows for ${keyToCheck}`);
          
          if (currentRows.length !== expectedEntries.length) {
            console.warn(`GRID MISMATCH AFTER 1 SECOND: ${gridId} has ${currentRows.length} rows but should have ${expectedEntries.length}`);
          }
        }
      });
    });
  }, 1000);
}

/**
 * Force complete replacement of grid data
 */
function forceReplaceGridData(historicalData) {
  console.log("FORCE REPLACING all reality grid data with historical data");
  
  // Map of grids and their data sources
  const gridMappings = [
    { gridId: 'realityTimeTable', data: historicalData.time_entries || [] },
    { gridId: 'realityMaterialsTable', data: historicalData.material_entries || [] },
    { gridId: 'realityAdjustmentsTable', data: historicalData.adjustment_entries || [] }
  ];
  
  // Process each grid
  gridMappings.forEach(mapping => {
    const { gridId, data } = mapping;
    
    if (!window.grids || !window.grids[gridId] || !window.grids[gridId].api) {
      console.error(`Grid not found or no API: ${gridId}`);
      return;
    }
    
    const api = window.grids[gridId].api;
    
    try {
      // Method 1: Try to completely clear the grid
      console.log(`Method 1: Clearing grid ${gridId} (via removal)`);
      const allRows = [];
      api.forEachNode(node => allRows.push(node.data));
      
      if (allRows.length > 0) {
        console.log(`Removing ${allRows.length} existing rows`);
        api.applyTransaction({ remove: allRows });
      }
      
      // Method 2: Try to completely replace the grid data
      console.log(`Method 2: Replacing grid ${gridId} data with ${data.length} historical entries`);
      
      // Some versions of AG Grid use setRowData, others use applyTransaction
      if (typeof api.setRowData === 'function') {
        console.log(`Using setRowData for ${gridId}`);
        api.setRowData(data);
      } else {
        console.log(`Using applyTransaction for ${gridId}`);
        api.applyTransaction({ add: data });
      }
      
      // Method 3: Force refresh
      console.log(`Method 3: Force refreshing ${gridId}`);
      if (typeof api.refreshCells === 'function') {
        api.refreshCells({ force: true });
      }
      
      console.log(`Grid ${gridId} updated successfully with ${data.length} entries`);
    } catch (error) {
      console.error(`Error updating grid ${gridId}:`, error);
    }
  });
  
  // Update totals based on historical data
  updateTotals(historicalData);
}

/**
 * Create a banner indicating historical data view
 */
function createHistoricalBanner(dateString) {
  // Remove any existing banner
  const existingBanner = document.getElementById('historical-banner');
  if (existingBanner) {
    existingBanner.remove();
  }
  
  // Create new banner
  const banner = document.createElement('div');
  banner.id = 'historical-banner';
  banner.className = 'alert alert-info text-center';
  banner.style.position = 'sticky';
  banner.style.top = '0';
  banner.style.zIndex = '1000';
  
  // Create date string
  let dateDisplay = 'Historical Data';
  if (dateString) {
    try {
      const date = new Date(dateString);
      dateDisplay = `Historical Data from ${date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      })}`;
    } catch (e) {
      console.error("Error formatting date:", e);
    }
  }
  
  banner.innerHTML = `<strong>${dateDisplay}</strong> - You are viewing historical data that cannot be modified`;
  
  // Add to document
  document.body.insertBefore(banner, document.body.firstChild);
}

/**
 * Debug utility: Log the current state of grids
 */
function logGridState(phase) {
  console.log(`GRID STATE [${phase}]:`);
  
  const gridIds = ['realityTimeTable', 'realityMaterialsTable', 'realityAdjustmentsTable'];
  
  gridIds.forEach(gridId => {
    if (window.grids && window.grids[gridId] && window.grids[gridId].api) {
      const api = window.grids[gridId].api;
      const rows = [];
      
      api.forEachNode(node => {
        rows.push(node.data);
      });
      
      console.log(`Grid ${gridId}: ${rows.length} rows`);
      if (rows.length > 0) {
        console.log(`Sample data:`, rows[0]);
      }
    } else {
      console.log(`Grid ${gridId}: Not found or no API`);
    }
  });
}

/**
 * Load current job data
 */
function loadCurrentData() {
  console.log("Loading current job data");
  
  // Get current data
  const currentData = window.latest_job_pricings_json || {};
  console.log("Current job data available:", !!currentData);
  
  // Update reality section with current data
  if (currentData.reality_pricing) {
    console.log("Refreshing reality section with current data");
    refreshGridWithCurrentData('reality', currentData.reality_pricing);
  } else {
    console.error("No reality_pricing found in current data");
  }
  
  // Remove historical mode indicator
  document.body.classList.remove('viewing-historical-data');
  const banner = document.getElementById('historical-banner');
  if (banner) {
    banner.remove();
  }
}

/**
 * Refresh a grid with current data
 */
function refreshGridWithCurrentData(section, data) {
  console.log(`Refreshing ${section} section with current data`);
  
  // For time, materials, and adjustments
  ['Time', 'Materials', 'Adjustments'].forEach(entryType => {
    const gridKey = `${section}${entryType}Table`;
    const entriesKey = `${entryType.toLowerCase()}_entries`;
    
    console.log(`Checking grid ${gridKey} for entries ${entriesKey}`);
    
    if (window.grids && window.grids[gridKey] && window.grids[gridKey].api) {
      const entries = data[entriesKey] || [];
      console.log(`Updating ${gridKey} with ${entries.length} entries`);
      
      try {
        const api = window.grids[gridKey].api;
        
        // Get existing rows
        const existingRows = [];
        api.forEachNode(node => {
          existingRows.push(node.data);
        });
        
        // Remove existing rows then add new ones
        if (existingRows.length > 0) {
          api.applyTransaction({ remove: existingRows });
        }
        
        // Add new entries
        if (entries.length > 0) {
          api.applyTransaction({ add: entries });
        }
        
        console.log(`Successfully updated ${gridKey} with current data`);
      } catch (error) {
        console.error(`Error updating grid ${gridKey}:`, error);
      }
    } else {
      console.error(`Grid ${gridKey} not found or has no API`);
    }
  });
}

// Helper function to capitalize first letter
function capitalize(string) {
  return string.charAt(0).toUpperCase() + string.slice(1);
}

/**
 * Set the display to show the historical date
 */
function setHistoricalDateDisplay(dateString) {
  try {
    // Parse the ISO date string
    const date = new Date(dateString);
    
    // Format the date for display
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    const formattedDate = date.toLocaleDateString('en-US', options);
    
    // Update the date in the central display element (the one showing "Current Data")
    const monthDisplay = document.getElementById('currentHistoricalMonth');
    if (monthDisplay) {
      monthDisplay.textContent = formattedDate;
      console.log(`Date display set to: ${formattedDate}`);
    } else {
      console.error("Could not find element with ID 'currentHistoricalMonth'");
    }
  } catch (error) {
    console.error("Error setting historical date display:", error);
  }
}

/**
 * Set the display to show 'Current Data'
 */
function setCurrentDateDisplay() {
  const monthDisplay = document.getElementById('currentHistoricalMonth');
  if (monthDisplay) {
    monthDisplay.textContent = 'Current Data';
    console.log(`Date display set to: Current Data`);
  } else {
    console.error("Could not find element with ID 'currentHistoricalMonth'");
  }
}

// New utility function to force clear a grid
function forceGridDataClear(gridId) {
  console.log(`Force clearing data for grid: ${gridId}`);
  
  // Try all possible methods to clear the grid
  const grid = window.grids?.[gridId];
  if (!grid) return false;
  
  try {
    // Method 1: Use AG Grid API if available
    if (grid.api && typeof grid.api.setRowData === 'function') {
      grid.api.setRowData([]);
      console.log(`Cleared ${gridId} using api.setRowData`);
      return true;
    }
    
    // Method 2: Try to access the gridOptions API
    if (grid.gridOptions && grid.gridOptions.api && 
        typeof grid.gridOptions.api.setRowData === 'function') {
      grid.gridOptions.api.setRowData([]);
      console.log(`Cleared ${gridId} using gridOptions.api.setRowData`);
      return true;
    }
    
    // Method 3: Try to access the raw DOM element
    const gridElement = document.getElementById(gridId);
    if (gridElement && gridElement.classList.contains('ag-theme-alpine')) {
      // For AG Grid, try to find and manipulate the internal row container
      const rowContainer = gridElement.querySelector('.ag-center-cols-container');
      if (rowContainer) {
        rowContainer.innerHTML = '';
        console.log(`Cleared ${gridId} by emptying row container DOM`);
        return true;
      }
    }

    // Method 4: Last resort - try to completely reinitialize the grid
    if (typeof window.reinitializeGrid === 'function') {
      window.reinitializeGrid(gridId, { rowData: [] });
      console.log(`Cleared ${gridId} by reinitialization`);
      return true;
    }
    
    return false;
  } catch (error) {
    console.error(`Error clearing grid ${gridId}:`, error);
    return false;
  }
}

// Update the updateEntriesGrid function to use the force clearing method
function updateEntriesGrid(section, entryType, entriesData) {
  console.log(`Updating ${section} ${entryType} grid with ${entriesData.length} entries`);
  
  // Fix capitalization for grid IDs (first letter of section is lowercase)
  const complexGridId = section + 
    (entryType === 'time' ? 'TimeTable' : 
     entryType === 'material' ? 'MaterialsTable' : 
     'AdjustmentsTable');
  
  // Correct capitalization for simple grid IDs
  const sectionCap = section.charAt(0).toUpperCase() + section.slice(1);
  const simpleGridId = 'simple' + sectionCap + 
    (entryType === 'time' ? 'TimeTable' : 
     entryType === 'material' ? 'MaterialsTable' : 
     'AdjustmentsTable');
  
  // Check if itemized pricing is on or off
  const isItemizedOn = document.getElementById('toggleGridButton')?.checked;
  
  // Define primary and fallback grid IDs based on current toggle state
  const primaryGridId = isItemizedOn ? complexGridId : simpleGridId;
  const fallbackGridId = isItemizedOn ? simpleGridId : complexGridId;
  
  console.log(`Trying to update primary grid: ${primaryGridId}, fallback: ${fallbackGridId}`);
  
  // CRITICAL: First force clear both grids before updating
  forceGridDataClear(primaryGridId);
  forceGridDataClear(fallbackGridId);
  
  // Now attempt to update the primary grid
  let updated = updateSingleGrid(primaryGridId, entriesData);
  
  // If primary update failed, try the fallback
  if (!updated) {
    console.log(`Primary grid ${primaryGridId} update failed, trying fallback ${fallbackGridId}`);
    updated = updateSingleGrid(fallbackGridId, entriesData);
  }
  
  if (!updated) {
    console.error(`Failed to update either grid for ${section} ${entryType}`);
  }
  
  return updated;
}

// Helper function to update a single grid
function updateSingleGrid(gridId, data) {
  const grid = window.grids?.[gridId];
  if (!grid) {
    console.log(`Grid ${gridId} not found or not initialized`);
    return false;
  }
  
  try {
    console.log(`Updating grid ${gridId} with data`);
    
    // Try different approaches to update the grid data
    if (typeof grid.setData === 'function') {
      grid.setData(data);
      return true;
    } else if (grid.api && typeof grid.api.setRowData === 'function') {
      grid.api.setRowData(data);
      return true;
    } else if (grid.gridOptions && grid.gridOptions.api && 
               typeof grid.gridOptions.api.setRowData === 'function') {
      grid.gridOptions.api.setRowData(data);
      return true;
    } else {
      // Try accessing the internal state directly (AG Grid specific)
      if (grid._internalState) {
        grid._internalState.rowData = data;
        grid.api.refreshCells({ force: true });
        return true;
      }
      return false;
    }
  } catch (err) {
    console.error(`Error updating grid ${gridId}:`, err);
    return false;
  }
}

/**
 * Update totals based on historical data
 */
function updateTotals(historicalData) {
  console.log("Updating totals with historical data");
  
  // Check if we have the revenue and cost grids
  if (!window.grids) {
    console.error("window.grids is undefined, cannot update totals");
    return;
  }
  
  // Update revenue and cost tables for each section
  const sections = ['reality', 'estimate', 'quote'];
  
  sections.forEach(section => {
    updateSectionTotals(section, historicalData);
  });
}

/**
 * Update totals for a specific section
 */
function updateSectionTotals(section, historicalData) {
  console.log(`Updating ${section} totals`);
  
  // Revenue table
  const revenueGridId = `${section}RevenueTable`;
  const costsGridId = `${section}CostsTable`;
  
  if (window.grids && 
      window.grids[revenueGridId] && window.grids[revenueGridId].api &&
      window.grids[costsGridId] && window.grids[costsGridId].api) {
    
    try {
      // Update revenue table
      const revenueApi = window.grids[revenueGridId].api;
      const revenueRows = [];
      
      // Get current rows
      revenueApi.forEachNode(node => {
        revenueRows.push(node.data);
      });
      
      // Update the values
      if (revenueRows.length >= 4) {
        // Get historical values with appropriate prefixes
        revenueRows[0][section] = historicalData[`${section}_time_revenue`] || 0;
        revenueRows[1][section] = historicalData[`${section}_material_revenue`] || 0;
        revenueRows[2][section] = historicalData[`${section}_adjustment_revenue`] || 0;
        revenueRows[3][section] = historicalData[`${section}_total_revenue`] || 0;
        
        // Apply the updates
        revenueApi.applyTransaction({ update: revenueRows });
        console.log(`${section} revenue table updated`);
      }
      
      // Update cost table
      const costsApi = window.grids[costsGridId].api;
      const costRows = [];
      
      // Get current rows
      costsApi.forEachNode(node => {
        costRows.push(node.data);
      });
      
      // Update the values
      if (costRows.length >= 4) {
        costRows[0][section] = historicalData[`${section}_time_cost`] || 0;
        costRows[1][section] = historicalData[`${section}_material_cost`] || 0;
        costRows[2][section] = historicalData[`${section}_adjustment_cost`] || 0;
        costRows[3][section] = historicalData[`${section}_total_cost`] || 0;
        
        // Apply the updates
        costsApi.applyTransaction({ update: costRows });
        console.log(`${section} cost table updated`);
      }
      
      // Force refresh
      revenueApi.refreshCells({ force: true });
      costsApi.refreshCells({ force: true });
      
    } catch (error) {
      console.error(`Error updating ${section} totals:`, error);
    }
  } else {
    console.log(`${section} revenue or cost tables not found - may be normal if tab isn't active`);
  }
}

function compareGridContents(gridId, expectedEntries) {
  if (!window.grids || !window.grids[gridId] || !window.grids[gridId].api) {
    console.error(`Can't compare grid ${gridId} - grid not found or no API`);
    return;
  }
  
  const api = window.grids[gridId].api;
  const actualRows = [];
  api.forEachNode(node => actualRows.push(node.data));
  
  console.log(`GRID COMPARISON for ${gridId}:`);
  console.log(`- Expected: ${expectedEntries.length} entries`);
  console.log(`- Actual: ${actualRows.length} entries`);
  
  if (actualRows.length !== expectedEntries.length) {
    console.warn(`MISMATCH: Grid has ${actualRows.length} rows but should have ${expectedEntries.length}`);
    
    // Log first entries for comparison
    if (actualRows.length > 0 && expectedEntries.length > 0) {
      console.log("First actual row:", actualRows[0]);
      console.log("First expected row:", expectedEntries[0]);
    }
  }
  
  return {
    matches: actualRows.length === expectedEntries.length,
    actual: actualRows,
    expected: expectedEntries
  };
}

function isInHistoricalMode() {
  return isViewingHistorical;
}

window.isInHistoricalMode = isInHistoricalMode;

// Add this function to be called at the beginning of loadHistoricalData
function inspectAllGrids() {
  console.log("=== LISTING ALL AVAILABLE GRID IDs ===");
  
  if (window.grids) {
    const gridIds = Object.keys(window.grids);
    console.log(`Found ${gridIds.length} grid IDs:`);
    
    gridIds.forEach(id => {
      const grid = window.grids[id];
      const hasAPI = grid && grid.api ? "yes" : "no";
      console.log(`- ${id} (has API: ${hasAPI})`);
      
      if (grid && grid.api) {
        // Log info about the API capabilities
        const capabilities = [];
        if (typeof grid.api.setRowData === 'function') capabilities.push('setRowData');
        if (typeof grid.api.getRowData === 'function') capabilities.push('getRowData');
        if (typeof grid.api.sizeColumnsToFit === 'function') capabilities.push('sizeColumnsToFit');
        
        if (capabilities.length > 0) {
          console.log(`  - API capabilities: ${capabilities.join(', ')}`);
        }
      }
    });
  } else {
    console.warn("No window.grids object found!");
  }
  
  // Also inspect related globals
  if (window.agGrid) {
    console.log("AG Grid is available globally");
  }
}
