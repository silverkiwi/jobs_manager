import { ActiveJobCellEditor } from './job_cell_editor.js';
import { rowStateTracker, timesheet_data } from './state.js';
import { currencyFormatter, hasRowChanged, validateAndTrackRow } from './utils.js';
import { createNewRow, calculateAmounts } from './grid_manager.js';
import { updateSummarySection } from './summary.js';
import { debouncedAutosave, markEntryAsDeleted } from './timesheet_autosave.js'
import { renderMessages } from './messages.js';


function deleteIconCellRenderer() {
    return `<span class="delete-icon">🗑️</span>`;
}

function getStatusIcon(status) {
    const icons = {
        'quoting': '📝',
        'approved': '✅',
        'rejected': '❌', 
        'in_progress': '🚧',
        'on_hold': '⏸️',
        'special': '⭐',
        'completed': '✔️',
        'archived': '📦'
    };
    return icons[status] || '';
}  

export const gridOptions = {
    columnDefs: [
        {
            field: 'id',
            hide: true, // Hidden column for the database ID
            editable: false,
        },
        {
            field: 'job_number',
            headerName: 'Job #',
            flex: 1,
            minWidth: 100,
            editable: true,
            cellEditor: ActiveJobCellEditor,
            cellEditorParams: {
                values: timesheet_data.jobs.map(job => job.job_display_name)
            },
            cellStyle: params => {
                const job = timesheet_data.jobs.find(j => j.job_number === params.value);

                if (!job) return null;

                const jobStatus = job.job_status;
                const hoursSpent = job.hours_spent;
                const estimatedHours = job.estimated_hours;
                console.log('Job status:', job.job_status);
                console.log('Hours spent:', hoursSpent);
                console.log('Estimated hours:', estimatedHours);

                if (jobStatus === 'completed' && hoursSpent > estimatedHours) {
                    return { backgroundColor: '#f8d7da' };
                }

                if (jobStatus === 'quoting') {
                    return { backgroundColor: '#fff3cd' };
                }

                if (hoursSpent > estimatedHours) {
                    return { backgroundColor: '#f8d7da' };
                }

                if (hoursSpent > estimatedHours * 0.8) {
                    return { backgroundColor: '#fff3cd' };
                }

                return null;
            },
            cellRenderer: params => {
                const job = timesheet_data.jobs.find(j => j.job_number === params.value);

                if (!job) return params.value;

                let { job_status, hours_spent, estimated_hours } = job;
                console.log(`Job number: ${job.job_number} | Job:`, job);
                console.log('Job status:', job_status);
                console.log('Hours spent:', hours_spent);
                console.log('Estimated hours:', estimated_hours);

                hours_spent = Number(hours_spent).toFixed(1);
                estimated_hours = Number(estimated_hours).toFixed(1);

                let statusIcon = '';
                statusIcon = getStatusIcon(job_status);

                if (job_status === 'completed' && hours_spent >= estimated_hours) {
                    renderMessages([{ level: 'warning', message: 'Adding hours to a job with status: "completed"!' }]); 
                    renderMessages([{ level: 'warning', message: 'Job has met or exceeded its estimated hours!' }]);
                    return `
                        ${statusIcon} <a href="/job/${job.id}">${params.value}
                        <small style="color: red">⚠ ${hours_spent}/${estimated_hours} hrs</small>
                        <small><strong> Warning:</strong> Exceeds estimated hours on completed job!</small>
                        </a>
                    `;
                }

                if (job_status === 'quoting') {
                    renderMessages([{ level: 'warning', message: 'Adding hours to a job with status: "quoting"!' }]);
                    return `
                        ${statusIcon} <a href="/job/${job.id}">${params.value}
                        <small style="color: orange">⚠ ${hours_spent}/${estimated_hours}hrs</small>
                        <small><strong>Note:</strong> Adding hours to quoting job.</small>
                        </a>
                    `;
                }

                return `
                    ${statusIcon} <a href="/job/${job.id}">
                    ${params.value}
                    <small>Total: ${hours_spent}/${estimated_hours} hrs</small>
                    </a>
                `;
            }
        },
        {
            field: 'description',
            headerName: 'Description',
            flex: 2,
            minWidth: 150,
            editable: true
        },
        {
            field: 'hours',
            headerName: 'Hours',
            flex: 1,
            minWidth: 80,
            editable: true,
            type: 'numericColumn',
            valueParser: params => Number(params.newValue),
            valueFormatter: params => params.value?.toFixed(2),
            cellStyle: params => {
                if (params.data.hours > params.data.scheduled_hours) {
                    return { backgroundColor: '#fff3cd' };
                }
                return null;
            },
            cellRenderer: params => {
                console.log('Rendering hours cell:', params.value, params.data);

                if (params.data.hours > params.data.scheduled_hours) {
                    return `<div style="background-color: #fff3cd">⚠️ ${Number(params.value).toFixed(2)}</div>`
                }
                return Number(params.value).toFixed(2) || '';
            }
        },
        {
            field: 'is_billable',
            headerName: 'Billable',
            width: 60,
            editable: true,
            cellRenderer: 'agCheckboxCellRenderer'
        },
        {
            field: 'notes',
            headerName: 'Notes',
            flex: 2,
            minWidth: 150,
            editable: true
        },
        {
            field: 'rate_type',
            headerName: 'Rate',
            width: 70,  // Set a specific width to make it smaller
            maxWidth: 70,  // REALLY TRY AND MAKE IT SMALLER
            editable: true,
            cellEditor: 'agSelectCellEditor',
            cellEditorParams: {
                values: ['Ord', '1.5', '2.0', 'Unpaid']
            }
        },
        {
            field: 'job_name',
            headerName: 'Job Name',
            width: 100,
            editable: false
        },
        {
            field: 'client', headerName: 'Client',
            width: 100,
            editable: false
        },
        {
            field: 'wage_amount',
            headerName: 'Wage $',
            width: 70,
            valueFormatter: currencyFormatter,
            editable: false
        },
        {
            field: 'bill_amount',
            headerName: 'Bill $',
            width: 70,
            valueFormatter: currencyFormatter,
            editable: false
        },
        {
            field: 'job_data',
            headerName: 'Job Data',
            width: 0,
            hide: true, // Invisible column to make processing easier
            editable: false
        },
        {
            field: 'staff_id',
            hide: true,  // Invisible column
            editable: false
        },
        {
            field: 'timesheet_date',
            hide: true,  // Invisible column
            editable: false
        },
        {
            headerName: '',
            width: 50,
            cellRenderer: deleteIconCellRenderer,
            onCellClicked:
                /**
                 * Handles the deletion of a row when a cell is clicked in the grid.
                 * 
                 * @param {Object} params - The cell click event parameters from ag-Grid
                 * @param {Object} params.api - The grid API
                 * @param {Object} params.node - The row node that was clicked
                 * @param {Object} params.node.data - The data for the clicked row
                 * 
                 * Business Logic:
                 * - Prevents deletion of the last remaining row in the grid
                 * - Assigns temporary IDs to new rows that haven't been saved
                 * - Marks existing entries for deletion in the backend
                 * - Removes the row from the grid's display
                 * - Updates the row state tracking in localStorage
                 * - Triggers an autosave after deletion
                 * 
                 * Safety Features:
                 * - Maintains at least one row in the grid at all times
                 * - Preserves deletion history for backend synchronization
                 * - Handles both new (unsaved) and existing rows appropriately
                 * 
                 * Dependencies:
                 * - Requires markEntryAsDeleted function
                 * - Requires debouncedAutosave function
                 * - Requires rowStateTracker object
                 */
                (params) => {
                    const rowCount = params.api.getDisplayedRowCount();
                    const rowData = params.node.data;

                    console.log('Delete clicked for row:', {
                        id: rowData.id,
                        rowCount: rowCount,
                        data: rowData
                    });

                    const isEmptyRow = !rowData.job_number && !rowData.description?.trim() && rowData.hours <= 0;

                    if (isEmptyRow) {
                        console.log('Skipping empty row:', rowData);
                        params.api.applyTransaction({ remove: [rowData] });
                        return;
                    }

                    if (rowData.id == null) {
                        console.log('Assigning temporary ID to new row:', rowData);
                        rowData.id = 'tempId';
                    }

                    // Mark for deletion first if it has an ID
                    if (rowData.id) {
                        console.log('Marking entry for deletion:', rowData.id);
                        markEntryAsDeleted(rowData.id);
                    }

                    // Then remove from grid
                    params.api.applyTransaction({ remove: [rowData] });
                    delete rowStateTracker[rowData.id];
                    localStorage.setItem('rowStateTracker', JSON.stringify(rowStateTracker));
                    console.log('Row removed from grid, triggering autosave');
                    debouncedAutosave();

                    if (rowCount === 1) {
                        console.log('Adding a new row to keep the grid populated');
                        params.api.applyTransaction({ add: [createNewRow()] })
                    }

                    updateSummarySection();
                }
        }
    ],
    defaultColDef: {
        flex: 1,
        minWidth: 100,
        sortable: false,
        filter: false
    },
    onCellValueChanged: (params) => {
        console.log('onCellValueChanged triggered:', params);

        // If job number changes, update job name, client, and job_data
        if (params.column?.colId === 'job_number') {
            console.log('Job number changed:', params.newValue);
            const job = timesheet_data.jobs.find(j => j.job_number === params.newValue);

            if (!job) return;

            job.hours_spent += Number(params.newValue || 0);
            params.node.setDataValue('job_name', job.name);
            params.node.setDataValue('client', job.client_name);
            params.node.setDataValue('job_data', job);
            params.node.setDataValue('hours_spent', job.hours_spent);
            params.node.setDataValue('estimated_hours', job.estimated_hours);

            calculateAmounts(params.node.data);
            console.log('Refreshing cells for job_name, job_number, client, wage_amount, bill_amount');
            params.api.refreshCells({
                rowNodes: [params.node],
                force: true 
            });
        }

        // Recalculate amounts if rate type or hours changes
        if (['rate_type', 'hours'].includes(params.column?.colId)) {
            console.log('Rate type or hours changed:', params.column?.colId, params.newValue);

            calculateAmounts(params.node.data);
            console.log('Refreshing cells for wage_amount, bill_amount');
            params.api.refreshCells({
                rowNodes: [params.node],
                force: true 
            });

            // Check for hours exceeding scheduled hours
            if (params.column?.colId === 'hours') {
                const totalHours = params.data.hours;
                const scheduled_hours = timesheet_data.staff.scheduled_hours;

                if (totalHours > scheduled_hours) {
                    renderMessages([{ level: 'warning', message: `Hours exceed scheduled (${totalHours} > ${scheduled_hours}).` }]);
                    params.node.setDataValue('inconsistent', true);
                } else {
                    params.node.setDataValue('inconsistent', false);
                }
                params.api.refreshCells({
                    rowNodes: [params.node],
                    force: true
                });
            }
        }

        if (!(params.source === 'edit')) {
            console.log('Skipping autosave - not an edit event');
            return;
        }

        debouncedAutosave();
        updateSummarySection();
    },
    // Add new row when Enter is pressed on last row
    onCellKeyDown: (params) => {
        if (params.event.key === 'Enter') {
            const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
            if (isLastRow) {
                params.api.applyTransaction({ add: [createNewRow()] });
                // Focus the first editable cell of the newly added row
                const newRowIndex = params.api.getDisplayedRowCount() - 1;
                params.api.setFocusedCell(newRowIndex, 'job_number');
                debouncedAutosave();
                updateSummarySection();
            }
        }
    },
};