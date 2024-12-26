import { ActiveJobCellEditor } from './job_cell_editor.js'; 
import { rowStateTracker, timesheet_data  } from './state.js';
import { currencyFormatter, hasRowChanged } from './utils.js';
import { createNewRow, calculateAmounts } from './grid_manager.js';
import { updateSummarySection } from './summary.js';


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
                if (job.job_status === 'completed') {
                    return `❓ <a href="/job/${job.id}">${params.value}</a>`;
                }
                if (job.job_status === 'quoting') {
                    return `❓ <a href="/job/${job.id}">${params.value}</a>`;
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
                return { backgroundColor: '#ffffff' };
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
                console.log('node id: ', params.node.data.id);

                if (params.node.data.id == null) {
                    params.node.data.id = 'tempId';
                }

                console.log('Delete clicked for row:', {
                    id: params.node.data.id,
                    rowCount: rowCount,
                    data: params.node.data
                });

                // Only proceed if we have more than one row
                if (rowCount > 1) {
                    // Mark for deletion first if it has an ID
                    if (params.node.data.id) {
                        console.log('Marking entry for deletion:', params.node.data.id);
                        markEntryAsDeleted(params.node.data.id);
                    }

                    // Then remove from grid
                    params.api.applyTransaction({
                        remove: [params.node.data]
                    });

                    delete rowStateTracker[params.node.data.id];
                    localStorage.setItem('rowStateTracker', JSON.stringify(rowStateTracker));
                    console.log('Row removed from grid, triggering autosave');
                    debouncedAutosave();
                    fetchJobs();
                } else {
                    console.log('Cannot delete last row');
                }
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

        const previousRowData = rowStateTracker[params.node.id] || {};
        const currentRowData = { ...params.node.data };

        console.log("previous row data: ", previousRowData);
        console.log("current row data: ", currentRowData);

        const rowChanged = hasRowChanged(previousRowData, currentRowData);
        console.log('Row changed:', rowChanged);

        if (!rowChanged) {
            return;
        }

        if (currentRowData.id == null) {
            currentRowData.id = 'tempId';
        }

        const isUserEdit = params.source === 'edit';

        // If job number changes, update job name, client, and job_data
        if (params.column?.colId === 'job_number') {
            console.log('Job number changed:', params.newValue);
            const job = timesheet_data.jobs.find(j => j.job_number === params.newValue);
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
        if (['rate_type', 'hours'].includes(params.column?.colId)) {
            console.log('Rate type or hours changed:', params.column.colId, params.newValue);
            calculateAmounts(params.node.data);
            console.log('Refreshing cells for wage_amount, bill_amount');
            params.api.refreshCells({
                rowNodes: [params.node],
                columns: ['wage_amount', 'bill_amount']
            });
        }

        const rowData = params.node.data;

        const isValidRow = rowData.job_number && rowData.hours > 0 && (rowData.description.trim() !== '' || rowData.notes.trim() !== '');

        if (!isValidRow) {
            console.log('Insufficient data to save, ignoring autosave');
            return;
        }

        if (isUserEdit) {
            console.log('Is user edit? -> ', isUserEdit, 'Valid row? -> ', isValidRow);
            console.log('Row is valid and changed, triggering autosave');
            debouncedAutosave();
            updateSummarySection();
        }
    },
    // Add new row when Enter is pressed on last row
    onCellKeyDown: (params) => {
        if (params.event.key === 'Enter') {
            const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
            if (isLastRow) {
                const currentRowData = params.node.data;

                console.log("Job number? -> ", currentRowData.job_number);
                console.log("Hours? -> ", currentRowData.hours);
                console.log("Description? -> ", currentRowData.description && currentRowData.description.trim() !== '');
                console.log("Notes? -> ", currentRowData.notes && currentRowData.notes.trim() !== '');

                const isRowValid = Boolean(
                    currentRowData.hours > 0 &&
                    (currentRowData.description && currentRowData.description.trim() !== '')
                );

                params.api.applyTransaction({ add: [createNewRow()] });

                // Focus the first editable cell of the newly added row
                const newRowIndex = params.api.getDisplayedRowCount() - 1;
                params.api.setFocusedCell(newRowIndex, 'job_number');

                const previousRowData = rowStateTracker[params.node.id] || {};

                const rowChanged = hasRowChanged(previousRowData, currentRowData);
                if (!rowChanged) {
                    return;
                }

                rowStateTracker[params.node.id] = { ...currentRowData };
                localStorage.setItem('rowStateTracker', JSON.stringify(rowStateTracker));

                if (isRowValid) {
                    debouncedAutosave();
                    updateSummarySection();
                }                
            }
        }
    }
};