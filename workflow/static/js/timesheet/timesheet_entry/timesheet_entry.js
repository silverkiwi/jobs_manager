import { triggerAutoCalculationForAllRows, createNewRow, initializeGrid,  } from "./grid_manager.js";
import { gridOptions } from "./grid.js";
import { getCookie } from "./utils.js";
import { timesheet_data, rowStateTracker, sentMessages } from './state.js';
import { fetchJobs } from "./job_section.js";
import { updateSummarySection } from "./summary.js";


window.timesheet_data = timesheet_data;
const csrftoken = getCookie('csrftoken');

const gridDiv = document.querySelector('#timesheet-grid');
initializeGrid(gridDiv, gridOptions);

document.addEventListener('DOMContentLoaded', function () {
    sentMessages.clear();

    fetchJobs();

    if (!localStorage.getItem('rowStateTracker')) {
        window.grid.addEventListener('firstDataRendered', () => {
            console.log('Grid data has been rendered. Initializing rowStateTracker.');
        
            const nodes = [];
            window.grid.forEachNode(node => {
                nodes.push(node);
            });
        
            console.log('Grid nodes:', nodes); // Verificar os nós após o carregamento dos dados
        
            nodes.forEach(node => {
                if (node.data && node.data.id) {
                    rowStateTracker[node.id] = { ...node.data };
                }
            });
        
            localStorage.setItem('rowStateTracker', JSON.stringify(rowStateTracker));
            console.log('Initial row state saved: ', rowStateTracker);
        });
    } else {
        console.log('Loaded rowStateTracker from localStorage.');
        Object.assign(rowStateTracker, JSON.parse(localStorage.getItem('rowStateTracker')));
        console.log('RowStateTracker: ', rowStateTracker);
    }    

    if (window.timesheet_data.time_entries?.length > 0) {
        window.grid.applyTransaction({ add: window.timesheet_data.time_entries });
        triggerAutoCalculationForAllRows();
    } else {
        window.grid.applyTransaction({
            add: [createNewRow()] 
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
});