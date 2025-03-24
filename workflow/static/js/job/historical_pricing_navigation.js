/**
 * Debug version of historical pricing navigation
 * Temporarily replace your current historical_pricing_navigation.js with this
 */

// State management for historical navigation
let currentHistoricalIndex = -1; // -1 means current data (not historical)
let historicalPricings = [];
let isViewingHistorical = false;

/**
 * Initialize the historical pricing navigation
 */
export function initHistoricalNavigation() {
  console.log("=== HISTORICAL NAVIGATION DEBUG ===");
  
  // Get historical pricing data from the page
  historicalPricings = window.historical_job_pricings_json || [];
  console.log("Historical pricing records found:", historicalPricings.length);
  
  if (historicalPricings.length > 0) {
    console.log("First historical record sample:", historicalPricings[0]);
  } else {
    console.warn("No historical pricing data available!");
  }
  
  // Only show navigation if we have historical data and job is special
  const jobStatus = document.getElementById('job_status')?.value;
  console.log("Current job status:", jobStatus);
  
  // Debug element existence
  ['historicalPricingNav', 'prevMonthBtn', 'nextMonthBtn', 'returnToCurrentBtn', 'currentHistoricalMonth'].forEach(id => {
    const element = document.getElementById(id);
    console.log(`Element #${id} exists:`, !!element);
  });
  
  if (historicalPricings.length > 0 && jobStatus === 'special') {
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
  addDebugButton();
}

/**
 * Navigate to the previous month's historical data
 */
function navigateToPreviousMonth() {
  console.log("Navigating to previous month");
  console.log("Current index:", currentHistoricalIndex, "Max index:", historicalPricings.length - 1);
  
  if (currentHistoricalIndex < historicalPricings.length - 1) {
    currentHistoricalIndex++;
    console.log("New index:", currentHistoricalIndex);
    loadHistoricalData(currentHistoricalIndex);
    updateNavigationButtons();
  } else {
    console.log("Already at oldest record, can't go further back");
  }
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
  prevBtn.disabled = currentHistoricalIndex >= historicalPricings.length - 1;
  nextBtn.disabled = currentHistoricalIndex <= -1;
  returnBtn.classList.toggle('d-none', currentHistoricalIndex === -1);
  
  // Update date display
  if (currentHistoricalIndex === -1) {
    monthDisplay.innerHTML = 'Current Data';
    monthDisplay.title = 'Viewing current job data';
    console.log("Date display set to: Current Data");
  } else {
    const historicalData = historicalPricings[currentHistoricalIndex];
    
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
  isViewingHistorical = (index !== -1);
  
  // Add this debug message
  console.log(`Loading historical data - isViewingHistorical set to: ${isViewingHistorical}`);
  
  // If returning to current data, reload the page to ensure fresh data
  if (index === -1) {
    console.log("Returning to current data - will reload all current data from server");
    // Store that we're returning to current view
    sessionStorage.setItem('returning_to_current_view', 'true');
    // Reload the page to get fresh data from server
    window.location.reload();
    return;
  }
  
  // If we're here, we're loading a historical snapshot
  const historicalData = jobPricingHistory[index];
  console.log(`Historical data to load: ${JSON.stringify(historicalData)}`);
  
  // Format date for display
  const dateStr = formatHistoricalDate(historicalData.created_at);
  document.getElementById('currentHistoricalMonth').textContent = dateStr;
  
  // Force more aggressive grid clearing - add this code
  console.log("Performing aggressive grid clearing before loading historical data");
  const allGridIds = Object.keys(window.grids || {});
  allGridIds.forEach(gridId => {
    if (window.grids[gridId] && window.grids[gridId].api) {
      console.log(`Force clearing grid: ${gridId}`);
      const api = window.grids[gridId].api;
      // Try multiple clearing methods
      api.setRowData([]);
      const rowCount = api.getDisplayedRowCount();
      if (rowCount > 0) {
        console.log(`Grid ${gridId} still has ${rowCount} rows - trying more aggressive clearing`);
        const allRowNodes = [];
        api.forEachNode(node => allRowNodes.push(node));
        if (allRowNodes.length > 0) {
          api.applyTransaction({ remove: allRowNodes.map(node => node.data) });
        }
      }
    }
  });
  
  // Then load the historical data into grids as before
  // Rest of your existing loading code...
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

/**
 * Update a specific entries grid with historical data
 */
function updateEntriesGrid(section, entryType, entries) {
  console.log(`Updating ${section} ${entryType} entries grid with ${entries.length} records`);
  
  // Generate grid ID based on section and entry type - FIX PLURALIZATION
  let gridId;
  if (entryType === 'material') {
    gridId = `${section}MaterialsTable`; // Note the plural "Materials"
  } else if (entryType === 'adjustment') {
    gridId = `${section}AdjustmentsTable`; // Note the plural "Adjustments"
  } else {
    gridId = `${section}${capitalize(entryType)}Table`;
  }
  
  console.log(`Setting ${entries.length} rows on grid: ${gridId}`);
  
  // Update the grid with historical entries
  try {
    if (!window.grids || !window.grids[gridId] || !window.grids[gridId].api) {
      console.log(`Grid ${gridId} not found or has no API - this may be normal if tab isn't active`);
      return;
    }
    
    const api = window.grids[gridId].api;
    
    // DEBUG: Log current contents before clearing
    console.log(`BEFORE CLEARING: ${gridId} current contents:`);
    const beforeRows = [];
    api.forEachNode(node => {
      beforeRows.push(node.data);
    });
    console.log(`${gridId} has ${beforeRows.length} rows before clearing`);
    
    // AGGRESSIVE GRID CLEARING - Method 1: Use setRowData with empty array
    console.log(`CLEARING GRID ${gridId} - Method 1: setRowData with empty array`);
    if (typeof api.setRowData === 'function') {
      api.setRowData([]);
    }
    
    // AGGRESSIVE GRID CLEARING - Method 2: Get and remove all rows
    console.log(`CLEARING GRID ${gridId} - Method 2: applyTransaction with remove`);
    const allRows = [];
    api.forEachNode(node => {
      allRows.push(node.data);
    });
    
    if (allRows.length > 0) {
      console.log(`Found ${allRows.length} rows still in grid ${gridId}, removing them all`);
      api.applyTransaction({ remove: allRows });
    }
    
    // VERIFICATION: Check grid is empty
    const verificationRows = [];
    api.forEachNode(node => {
      verificationRows.push(node.data);
    });
    
    if (verificationRows.length > 0) {
      console.warn(`CRITICAL: Grid ${gridId} still has ${verificationRows.length} rows after clearing!`);
      // Try one more extreme method - replace the grid model
      if (api.setRowData) {
        api.setRowData([]);
      }
    } else {
      console.log(`Grid ${gridId} successfully cleared - contains 0 rows`);
    }
    
    // Only now add the historical entries
    if (entries.length > 0) {
      // Create deep copies of the entries to avoid reference issues
      const entriesCopy = JSON.parse(JSON.stringify(entries));
      console.log(`Adding ${entriesCopy.length} historical entries to ${gridId}`);
      
      // DEBUG: Log the actual data being added
      console.log(`HISTORICAL DATA SAMPLE for ${gridId}:`, 
                 entriesCopy.length > 0 ? JSON.stringify(entriesCopy[0]) : "No entries");
      
      // Try setRowData first (complete replacement)
      if (typeof api.setRowData === 'function') {
        console.log(`Using setRowData for ${gridId}`);
        api.setRowData(entriesCopy);
      } else {
        // Fallback to applyTransaction
        console.log(`Using applyTransaction for ${gridId}`);
        api.applyTransaction({ add: entriesCopy });
      }
      
      // Force refresh
      api.refreshCells({ force: true });
      
      // Final verification
      const finalRows = [];
      api.forEachNode(node => {
        finalRows.push(node.data);
      });
      console.log(`AFTER UPDATE: Grid ${gridId} contains ${finalRows.length} rows (should be ${entries.length})`);
      
      // DEBUG: Log the actual data in the grid after update
      if (finalRows.length > 0) {
        console.log(`FINAL DATA SAMPLE for ${gridId}:`, JSON.stringify(finalRows[0]));
        
        // Compare keys to see if data structure matches expected
        if (entriesCopy.length > 0) {
          const expectedKeys = Object.keys(entriesCopy[0]).sort();
          const actualKeys = Object.keys(finalRows[0]).sort();
          console.log(`Expected keys: ${expectedKeys.join(', ')}`);
          console.log(`Actual keys: ${actualKeys.join(', ')}`);
          
          // Check if they're different
          const missingKeys = expectedKeys.filter(k => !actualKeys.includes(k));
          const extraKeys = actualKeys.filter(k => !expectedKeys.includes(k));
          
          if (missingKeys.length > 0) {
            console.warn(`MISSING KEYS in grid data: ${missingKeys.join(', ')}`);
          }
          if (extraKeys.length > 0) {
            console.warn(`EXTRA KEYS in grid data: ${extraKeys.join(', ')}`);
          }
        }
      }
    }
    
    console.log(`Successfully updated ${gridId} with historical data`);
  } catch (error) {
    console.error(`Error updating grid ${gridId}:`, error);
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

// Add function to check if we're returning from a historical view
function initializeAfterPageLoad() {
  if (sessionStorage.getItem('returning_to_current_view') === 'true') {
    console.log("Page reloaded after returning from historical view - ensuring fresh data");
    sessionStorage.removeItem('returning_to_current_view');
    // Force reload of all current data from the server
    // This might be a call to your data loading function or similar
  }
}

// Call this from your document ready function
document.addEventListener('DOMContentLoaded', function() {
  initializeAfterPageLoad();
  // Your other initialization code...
});
