import { triggerAutoCalculationForAllRows, createNewRow, initializeGrid,  } from "./grid_manager.js";
import { gridOptions } from "./grid.js";
import { getCookie } from "./utils.js";
import { initializeModals } from "./modal_handling.js";
import { initializePaidAbsenceHandlers } from "./paid_absence.js";
import { timesheet_data, rowStateTracker, sentMessages } from './state.js';
import { fetchJobs } from "./job_section.js";
import { updateSummarySection } from "./summary.js";


window.timesheet_data = timesheet_data;
const csrftoken = getCookie('csrftoken');

const gridDiv = document.querySelector('#timesheet-grid');
initializeGrid(gridDiv, gridOptions);

document.addEventListener('DOMContentLoaded', function () {
    // Clear sent messages
    console.log(sentMessages);
    sentMessages.clear();

    console.log('Fetching initial jobs:', window.timesheet_data.jobs);
    fetchJobs();

    // Initialize rowStateTracker
    window.grid.forEachNode(node => {
        rowStateTracker[node.id] = { ...node.data };
        localStorage.setItem('rowStateTracker', JSON.stringify(rowStateTracker));
    });
    console.log('Initial row state saved: ', rowStateTracker);

    // Load existing entries if any, otherwise add an empty row
    if (window.timesheet_data.time_entries?.length > 0) {
        window.grid.applyTransaction({ add: window.timesheet_data.time_entries });
        triggerAutoCalculationForAllRows();
    } else {
        window.grid.applyTransaction({
            add: [createNewRow()] // Use centralized function
        });
    }

    updateSummarySection();

    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    initializeModals();
    initializePaidAbsenceHandlers();
});