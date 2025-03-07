import { sections, workType } from '../grid/grid_initialization.js';
import { capitalize, calculateTotalRevenue, calculateTotalCost, checkRealityValues } from '../grid/grid_utils.js';

/**
 * @description Functions to extract and manipulate URL data,
 * primarily the Job ID which is used in almost all job-related actions
 * @returns {string} The job ID extracted from the URL path
 */
export function getJobIdFromUrl() {
  return window.location.pathname.split('/')[2];
}

/**
 * Collection of functions for formatting and displaying events on a timeline.
 * Includes utilities for date/time conversions and event type styling.
 * @module TimelineEvents
 */

/**
 * Formats an event type string by replacing underscores with spaces and capitalizing each word.
 * @param {string} eventType - Raw event type string containing underscores
 * @returns {string} Formatted event type with spaces and proper capitalization
 * @example
 * formatEventType('job_started') // returns 'Job Started'
 */
export function formatEventType(eventType) {
  return eventType
    .replaceAll('_', ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Formats a timestamp into a localized date and time string.
 * @param {string|number} timestamp - The timestamp to format (can be ISO string or Unix timestamp)
 * @returns {string} Formatted date string in the format 'MMM D, YYYY, HH:MM AM/PM'
 * @example
 * formatTimestamp('2023-12-25T15:00:00Z') // returns 'Dec 25, 2023, 03:00 PM'
 * formatTimestamp(1703516400000) // returns 'Dec 25, 2023, 03:00 PM'
 */
export function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  }).format(date);
}

/**
 * Adds a new event to the timeline by creating and inserting an HTML element.
 * @param {Object} event - The event object to add
 * @param {string} event.event_type - Type of the event
 * @param {string} event.timestamp - Timestamp of when the event occurred
 * @param {string} event.description - Description of the event
 * @param {string} event.staff - Name of staff member associated with the event
 * @param {HTMLElement} jobEventsList - DOM element containing the timeline
 * @returns {void}
 */
export function addEventToTimeline(event, jobEventsList) {
  const eventType = formatEventType(event.event_type);

  const newEventHtml = `
        <div class='timeline-item list-group-item'>
            <div class='d-flex w-100 justify-content-between'>
                <div class='timeline-date text-muted small'>${formatTimestamp(event.timestamp)}</div>
            </div>
            <div class='timeline-content'>
                <h6 class='mb-1'>${eventType}</h6>
                <p class='mb-1'>${event.description}</p>
                <small class='text-muted'>By ${event.staff}</small>
            </div>
        </div>
    `;
  jobEventsList.insertAdjacentHTML('afterbegin', newEventHtml);
}

/**
 * Toggle between simple and complex grid views
 * @param {string} mode - 'simple', 'complex', 'manual', or 'automatic' (reads from checkbox)
 */
export function toggleGrid(mode) {
  const toggleButton = document.getElementById('toggleGridButton');
  let isComplex;
  
  // Determine complex mode based on input mode
  switch (mode) {
    case 'automatic':
      isComplex = toggleButton ? toggleButton.checked : false;
      break;
    case 'manual':
      if (!toggleButton) return;
      isComplex = toggleButton.checked;
      toggleComplexJob();
      return; // toggleComplexJob will update the UI
    case 'complex':
      isComplex = true;
      if (toggleButton) toggleButton.checked = true;
      break;
    case 'simple':
      isComplex = false;
      if (toggleButton) toggleButton.checked = false;
      break;
    default:
      return; // Invalid mode, exit early
  }
  
  // Store the complex mode in the hidden field
  const complexJobElement = document.getElementById('complex-job');
  if (complexJobElement) {
    complexJobElement.textContent = isComplex.toString();
  }

  // Toggle visibility for estimate and quote sections
  ['estimate', 'quote'].forEach(section => {
    const advancedGrid = document.getElementById(`advanced-${section}-grid`);
    const simpleGrid = document.getElementById(`simple-${section}-grid`);
    
    if (!advancedGrid || !simpleGrid) return;
    
    advancedGrid.classList.toggle('d-none', !isComplex);
    simpleGrid.classList.toggle('d-none', isComplex);
  });

  // Reality section always uses advanced grid
  const realityAdvancedGrid = document.getElementById('advanced-reality-grid');
  const realitySimpleGrid = document.getElementById('simple-reality-grid');
  
  if (realityAdvancedGrid && realitySimpleGrid) {
    realityAdvancedGrid.classList.remove('d-none');
    realitySimpleGrid.classList.add('d-none');
  }
  
  // Make all simple totals tables visible
  ['simpleEstimateTotalsTable', 'simpleQuoteTotalsTable', 'simpleRealityTotalsTable'].forEach(tableId => {
    const table = document.getElementById(tableId);
    if (table) table.classList.remove('d-none');
  });

  // Refresh all grid sizes
  setTimeout(() => {
    Object.keys(window.grids).forEach(key => {
      const grid = window.grids[key];
      if (grid?.api) grid.api.sizeColumnsToFit();
    });
    
    calculateTotalRevenue();
    calculateTotalCost();
    checkRealityValues();
  }, 100);
}

/**
 * Toggles the pricing type UI elements and updates the pricing type on the server
 * @param {Event} event - DOM event object or object with value property
 */
export function togglePricingType(event) {
  if (!event) return;
  
  // Extract value from either event.target.value (DOM event) or event.value
  const newType = event.target?.value || event.value;
  if (!newType) return;
  
  const jobId = getJobIdFromUrl();
  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
  if (!csrfToken) {
    console.error("CSRF token not found");
    return;
  }

  // Make API call to update pricing type on the server
  fetch('/api/job/toggle-pricing-type/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify({
      job_id: jobId,
      pricing_type: newType,
    }),
  })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        alert(data.error);
        return;
      }

      const isTimeMaterials = newType === 'time_materials';
      
      // Update UI elements based on pricing type
      const elements = {
        quoteGrid: document.getElementById('quoteGrid'),
        quoteCheckbox: document.getElementById('quoteCheckbox'),
        copyEstimateButton: document.getElementById('copyEstimateToQuote')
      };
      
      // Toggle visibility for each element
      Object.values(elements).forEach(element => {
        if (element) element.classList.toggle('d-none', isTimeMaterials);
      });
    })
    .catch(err => {
      console.error(err);
      alert("Error updating pricing type.");
    });
}

/**
 * Handles toggle of complex job setting
 * Called when the toggle button is clicked
 * @returns {boolean} Whether the toggle was successful
 */
export function toggleComplexJob() {
  const toggleButton = document.getElementById("toggleGridButton");
  if (!toggleButton) return false;
  
  const isComplexElement = document.getElementById("complex-job");
  if (!isComplexElement) return false;
  
  const isComplex = isComplexElement.textContent.toLowerCase() === 'true';
  const newValue = toggleButton.checked;
  
  // No change needed if state hasn't changed
  if ((isComplex && newValue) || (!isComplex && !newValue)) {
    return true;
  }

  // Check if we can disable complex mode
  if (isComplex && !newValue) {
    const latestJobPricingsElement = document.getElementById("latestJobPricingsData");
    if (latestJobPricingsElement) {
      const pricingsData = JSON.parse(latestJobPricingsElement.textContent);
      
      // Check if any section has multiple pricing entries
      const hasMultipleEntries = sections.some(section => {
        if (!pricingsData[section]) return false;
        return workType.some(type => 
          pricingsData[section][type] && pricingsData[section][type].length > 1
        );
      });
      
      if (hasMultipleEntries) {
        alert("Cannot disable complex mode while multiple pricing entries exist.");
        toggleButton.checked = true;
        return false;
      }
    }
  }

  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")?.value;
  if (!csrfToken) {
    console.error("CSRF token not found");
    return false;
  }

  // Update complex job status on the server
  fetch('/api/job/toggle-complex-job/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    body: JSON.stringify({
      job_id: getJobIdFromUrl(),
      complex_job: newValue,
    }),
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      console.error('API returned error:', data.error);
      alert(data.error);
      toggleButton.checked = !toggleButton.checked;
      return;
    }
    
    isComplexElement.textContent = newValue.toString();
    
    // Update interface based on new complex job status
    toggleGrid(newValue ? 'complex' : 'simple');
  })
  .catch(err => {
    console.error('API request failed:', err);
    alert("Error updating complex mode.");
    toggleButton.checked = !toggleButton.checked;
  });

  return true;
}
