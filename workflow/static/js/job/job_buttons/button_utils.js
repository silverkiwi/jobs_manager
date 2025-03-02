import { sections, workType } from '../grid/grid_initialization.js';
import { capitalize } from '../grid/grid_utils.js';

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

export function toggleGrid(mode = "manual") {
  let validJob;

  if (mode === "manual") {
    validJob = toggleComplexJob();
  }

  // Only proceed with grid toggle if we're in auto mode or validJob was true
  if (mode === "automatic" || (mode === "manual" && validJob)) {
    const isSimple = document.getElementById('toggleGridButton')?.checked ?? false;
    switch (isSimple) {
      case true:
        sections.forEach((section) => {
          document.getElementById(`advanced-${section}-grid`).classList =
            'd-none';
          document.getElementById(`simple-${section}-grid`).classList = 'd-block';

          setTimeout(() => {
            workType.forEach((work) => {
              const simpleApi =
                window.grids[`simple${capitalize(section)}${work}Table`]?.api;
              simpleApi?.sizeColumnsToFit();
            });
          }, 50);
        });
        break;
      case false:
        sections.forEach((section) => {
          document.getElementById(`simple-${section}-grid`).classList = 'd-none';
          document.getElementById(`advanced-${section}-grid`).classList =
            'd-block';

          setTimeout(() => {
            workType.forEach((work) => {
              const advApi = window.grids[`${section}${work}Table`]?.api;
              advApi?.sizeColumnsToFit();
            });
          }, 50);
        });
        break;
    }
  }
}

function toggleComplexJob() {
  if (Environment.isDebugMode()) console.log('Starting checkComplexJob function');
  const toggleButton = document.getElementById("toggleGridButton");
  const isComplexElement = document.getElementById("complex-job");
  const isComplex = isComplexElement.textContent.toLowerCase() === 'true';
  if (Environment.isDebugMode()) console.log(`Current state: isComplex = ${isComplex}`);

  if (isComplex) {
    if (Environment.isDebugMode()) console.log('Checking if we can disable complex mode');
    const latestJobPricingsElement = JSON.parse(document.getElementById("latestJobPricingsData").textContent);
    if (Environment.isDebugMode()) console.log('Parsed job pricing data:', latestJobPricingsElement);
    const estimatePricing = latestJobPricingsElement.estimate_pricing;
    const quotePricing = latestJobPricingsElement.quote_pricing;
    const realityPricing = latestJobPricingsElement.reality_pricing;
    if (Environment.isDebugMode()) console.log('Extracted pricing data:', { estimatePricing, quotePricing, realityPricing });
    const pricings = [estimatePricing, quotePricing, realityPricing];

    // Check if any pricing has entries
    let hasEntries = false;
    pricings.forEach((pricing, index) => {
      if (Environment.isDebugMode()) console.log(`Checking pricing type ${index === 0 ? 'estimate' : index === 1 ? 'quote' : 'reality'}`);
      workType.forEach((work) => {
        const workLower = work.toLowerCase();
        const entriesKey = `${workLower}_entries`;
        // Check if the entries key exists before accessing length property
        if (pricing[entriesKey] && pricing[entriesKey].length > 1) {
          if (Environment.isDebugMode()) console.log(`Found ${workLower} entries, cannot disable complex mode`);
          alert("Cannot disable complex mode while job has pricing.");
          toggleButton.checked = true;
          hasEntries = true;
          return false;
        }
      });
      if (hasEntries) return false;
    });
    if (Environment.isDebugMode()) console.log('Complex mode check completed');
  }

  if (Environment.isDebugMode()) console.log('Sending API request to update complex job status');
  fetch('/api/job/toggle-complex-job/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector("[name=csrfmiddlewaretoken]").value,
    },
    body: JSON.stringify({
      job_id: getJobIdFromUrl(),
      complex_job: !isComplex,
    }),
  })
    .then(response => {
      if (Environment.isDebugMode()) console.log('Received API response', response);
      return response.json();
    })
    .then(data => {
      if (Environment.isDebugMode()) console.log('Processed API response data', data);
      if (data.error) {
        console.error('API returned error:', data.error);
        alert(data.error);
        toggleButton.checked = !toggleButton.checked;
      }
      isComplexElement.textContent = capitalize(String(!isComplex));
    })
    .catch(err => {
      console.error('API request failed:', err);
      alert("Error updating complex mode.");
      toggleButton.checked = !toggleButton.checked;
    });

  if (Environment.isDebugMode()) console.log('Completed checkComplexJob function');
  return true;
}

/**
 * Toggles the pricing type UI elements and updates the pricing type on the server
 * @param {Event|Object} event - DOM event object or object with value property
 */
export function togglePricingType(event) {
  // Extract value from either event.target.value (DOM event) or event.value (direct object)
  const newType = event.target?.value || event.value;

  const quoteGrid = document.getElementById('quoteGrid');
  const quoteCheckbox = document.getElementById('quoteCheckbox');
  const copyEstimate = document.getElementById('copyEstimateToQuote');

  const jobId = getJobIdFromUrl();

  fetch('/api/job/toggle-pricing-type/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector("[name=csrfmiddlewaretoken]").value,
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
      switch (newType) {
        case "time_materials":
          quoteGrid.classList.add('d-none');
          quoteCheckbox.classList.add('d-none');
          copyEstimate.classList.add('d-none');
          break;
        case "fixed_price":
          quoteGrid.classList.remove('d-none');
          quoteCheckbox.classList.remove('d-none');
          copyEstimate.classList.remove('d-none');
          break;
        default:
          break;
      }
    })
    .catch(err => {
      console.error(err);
      alert("Error updating pricing type.");
    });
}
