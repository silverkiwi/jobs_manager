import { ActiveJobCellEditor } from './job_cell_editor.js'; 
import { rowStateTracker, timesheet_data  } from './state.js';
import { currencyFormatter, hasRowChanged, validateAndTrackRow } from './utils.js';
import { createNewRow, calculateAmounts } from './grid_manager.js';
import { updateSummarySection } from './summary.js';
import { debouncedAutosave, markEntryAsDeleted } from './timesheet_autosave.js'


function deleteIconCellRenderer() {
    return `<span class="delete-icon">🗑️</span>`;
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
                if (job) {
                    console.log('Job status:', job.job_status);
                    if (job.job_status === 'completed') {
                        return { backgroundColor: '#f8d7da' };
                    }
                    if (job.job_status === 'quoting') {
                        return { backgroundColor: '#f8d7da' };
                    }
                }
                return null;
            },
            cellRenderer: params => {
                const job = timesheet_data.jobs.find(j => j.job_number === params.value);
                console.log('Rendering job:', job);
                if (job) {
                    if (job.job_status === 'completed') {
                        return `❓ <a href="/job/${job.id}">${params.value}</a>`;
                    }
                    if (job.job_status === 'quoting') {
                        return `❓ <a href="/job/${job.id}">${params.value}</a>`;
                    }
                }
                return params.value;
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

        const { colId, newValue } = params.column || {};

        // If job number changes, update job name, client, and job_data
        if (colId === 'job_number') {
            console.log('Job number changed:', newValue);
            const job = timesheet_data.jobs.find(j => j.job_number === newValue);
            if (job) {
                params.node.setDataValue('job_name', job.name);
                params.node.setDataValue('client', job.client_name);
                params.node.setDataValue('job_data', job); // Store the whole job object as job_data

                calculateAmounts(params.node.data);
                console.log('Refreshing cells for job_name, client, wage_amount, bill_amount');
                params.api.refreshCells({
                    rowNodes: [params.node],
                    columns: ['job_name', 'client', 'wage_amount', 'bill_amount']
                });
            }
        }

        // Recalculate amounts if rate type or hours changes
        if (['rate_type', 'hours'].includes(colId)) {
            console.log('Rate type or hours changed:', colId, newValue);
            calculateAmounts(params.node.data);
            console.log('Refreshing cells for wage_amount, bill_amount');
            params.api.refreshCells({
                rowNodes: [params.node],
                columns: ['wage_amount', 'bill_amount']
            });
        }

        // Verify if it's an user edition of the row
        if (params.source === 'edit') {
            if (colId === 'hours') {
                const totalHours = params.data.hours;
                const scheduled_hours = timesheet_data.staff.scheduled_hours;

                if (totalHours > scheduled_hours) {
                    renderMessages([{level: 'warning', message: `Hours exceed scheduled (${totalHours} > ${scheduled_hours}).`}]);
                    params.node.setDataValue('inconsistent', true);
                } else {
                    params.node.setDataValue('inconsistent', false);
                }
            }

            debouncedAutosave();
            updateSummarySection();
        } else {
            console.log('Skipping autosave due to invalid or unchanged row');
        }
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
    cellStyle: (params) => {
        if (params.data?.inconsistent) {
            return { backgroundColor: '#fff3cd', color: '#856404' };
        }
        return null;
    }
};