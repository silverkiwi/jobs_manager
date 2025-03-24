/**
 * Purchase Order Form Handling
 * 
 * Uses AG Grid for line items management, using the timesheet pattern
 */

import { debouncedAutosave, markLineItemAsDeleted } from './purchase_order_autosave.js';
import { ActiveJobCellEditor } from './job_cell_editor.js';

document.addEventListener('DOMContentLoaded', function() {
    // Parse JSON data - exactly like timesheet does
    const jobsData = JSON.parse(document.getElementById('jobs-data').textContent);
    const lineItemsData = document.getElementById('line-items-data') ?
        JSON.parse(document.getElementById('line-items-data').textContent) : [];
    
    window.purchaseData = {
        jobs: jobsData,
        lineItems: lineItemsData
    };
    
    console.log('Available jobs:', jobsData);
    console.log('Existing line items:', lineItemsData);
    
    // Set today's date for order date
    const today = new Date();
    const formattedDate = today.toISOString().split('T')[0]; // Format as YYYY-MM-DD
    document.getElementById('order_date').value = formattedDate;
    
    // Initialize line items grid
    const gridOptions = {
        columnDefs: [
            {
                headerName: 'Job',
                field: 'job',
                editable: true,
                cellEditor: ActiveJobCellEditor,
                valueFormatter: params => {
                    if (!params.value) return '';
                    const job = jobsData.find(j => j.id === params.value);
                    return job ? job.job_display_name : '';
                }
            },
            {
                headerName: 'Description',
                field: 'description',
                editable: true
            },
            {
                headerName: 'Quantity',
                field: 'quantity',
                editable: true,
                valueParser: params => {
                    if (params.newValue === '' || params.newValue === null) return 1;
                    return Number(params.newValue);
                }
            },
            {
                headerName: 'Unit Cost',
                field: 'unit_cost',
                editable: true,
                valueParser: params => {
                    // Empty value or 'TBC' should be stored as 'TBC'
                    if (params.newValue === '' || params.newValue === 'TBC') return 'TBC';
                    return Number(params.newValue);
                },
                valueFormatter: params => {
                    if (params.value === 'TBC') return 'TBC';
                    return `$${Number(params.value).toFixed(2)}`;
                },
                cellRenderer: params => {
                    if (params.value === 'TBC') return `<span class="text-muted">TBC</span>`;
                    return `$${Number(params.value).toFixed(2)}`;
                }
            },
            {
                headerName: 'Total',
                field: 'total',
                valueGetter: params => {
                    // Assert that quantity exists and is a number
                    console.assert(params.data.quantity !== undefined, 'Quantity is undefined');
                    
                    // Return TBC if unit_cost is TBC, otherwise calculate the total
                    return params.data.unit_cost === 'TBC' ? 'TBC' :
                        params.data.quantity * params.data.unit_cost;
                },
                valueFormatter: params => {
                    if (params.value === 'TBC') return 'TBC';
                    return `$${Number(params.value).toFixed(2)}`;
                },
                cellStyle: params => {
                    // Skip validation if job is empty (new row) or value is TBC
                    if (!params.data.job || params.value === 'TBC') return null;
                    
                    const jobId = params.data.job;
                    const job = jobsData.find(j => j.id === jobId);
                    
                    // Assert necessary conditions
                    console.assert(job, `Job with ID ${jobId} not found`);
                    console.assert(job.estimated_materials !== undefined,
                        `Job ${job.job_number} missing estimated_materials`);
                    
                    // Calculate total cost for this job from all rows
                    let jobTotal = 0;
                    window.grid.forEachNode(node => {
                        if (node.data.job === jobId && node.data.unit_cost !== 'TBC') {
                            jobTotal += node.data.quantity * node.data.unit_cost;
                        }
                    });
                    
                    return jobTotal > job.estimated_materials ? { backgroundColor: "#fff3cd" } : null;
                },
                cellRenderer: params => {
                    // If value is TBC, render it as such
                    if (params.value === 'TBC') return '<span class="text-muted">TBC</span>';
                    
                    // Format the value with currency
                    const formattedValue = `$${Number(params.value).toFixed(2)}`;
                    
                    // Skip validation if job is empty (new row)
                    if (!params.data.job) return formattedValue;
                    
                    const jobId = params.data.job;
                    const job = jobsData.find(j => j.id === jobId);
                    
                    // Assert necessary conditions
                    console.assert(job, `Job with ID ${jobId} not found`);
                    console.assert(job.estimated_materials !== undefined,
                        `Job ${job.job_number} missing estimated_materials`);
                    
                    // Calculate total cost for this job from all rows
                    let jobTotal = 0;
                    window.grid.forEachNode(node => {
                        if (node.data.job === jobId && node.data.unit_cost !== 'TBC') {
                            jobTotal += node.data.quantity * node.data.unit_cost;
                        }
                    });
                    
                    return jobTotal > job.estimated_materials
                        ? `<div style="background-color: #fff3cd">⚠️ ${formattedValue}</div>`
                        : formattedValue;
                }
            },
            {
                headerName: '',
                field: 'delete',
                width: 50,
                cellRenderer: deleteIconCellRenderer,
                onCellClicked: (params) => {
                    deleteRow(params.api, params.node);
                }
            }
        ],
        rowData: [],
        defaultColDef: {
            flex: 1,
            minWidth: 100,
            resizable: true
        },
        onCellValueChanged: onCellValueChanged,
        domLayout: 'autoHeight',
        // Handle keyboard navigation
        onCellKeyDown: (params) => {
            const { event, api, node, column } = params;
            const isLastRow = params.node.rowIndex === params.api.getDisplayedRowCount() - 1;
            const colId = column.getColId();
            
            // Handle different key combinations
            if (event.key === 'Enter') {
                if (colId === 'delete') {
                    // Delete row when Enter is pressed in delete column
                    deleteRow(api, node);
                } else if (colId === 'unit_cost' && !event.shiftKey) {
                    // Add new row when Enter is pressed in unit_cost column
                    event.stopPropagation();
                    createNewRowShortcut(api);
                    return false;
                }
            } else if (event.key === 'Tab' && !event.shiftKey && isLastRow && colId === 'unit_cost') {
                // Add new row when Tab is pressed in unit_cost column of last row
                createNewRowShortcut(api);
            }
        }
    };
    
    // Initialize the grid
    const gridDiv = document.querySelector('#purchase-order-lines-grid');
    window.grid = agGrid.createGrid(gridDiv, gridOptions);
    
    // Check if we have existing line items (for edit mode)
    const existingLineItems = window.purchaseData.lineItems || [];
    
    if (existingLineItems.length > 0) {
        // If we have existing line items, add them to the grid
        window.grid.applyTransaction({
            add: existingLineItems
        });
    } else {
        // Otherwise, initialize with one empty row
        window.grid.applyTransaction({
            add: [createNewRow()]
        });
    }
    
    // After grid initialization
    window.grid.addEventListener('firstDataRendered', function() {
        adjustGridHeight();
    });
    
    // Using autosave - no save button needed
    
    // Cell value change handler
    function onCellValueChanged(params) {
        // If this is the last row and contains data, add a new empty row
        const isLastRow = params.node.rowIndex === params.api.getDisplayedRowCount() - 1;
        const hasData = params.data.job || params.data.description ||
                        params.data.quantity !== '' || params.data.unit_cost !== '';
        
        if (isLastRow && hasData) {
            createNewRowShortcut(params.api);
        }
        
        // Determine which cells to refresh based on what changed
        const jobId = params.data.job;
        const affectsAllJobRows = ['job', 'quantity', 'unit_cost'].includes(params.colDef.field);
        
        if (jobId && affectsAllJobRows) {
            // Find all nodes with this job
            const nodesToRefresh = [];
            window.grid.forEachNode(node => {
                if (node.data.job === jobId) {
                    nodesToRefresh.push(node);
                }
            });
            
            // Assert we found at least this row
            console.assert(nodesToRefresh.length > 0, 'No rows found for job refresh');
            
            // Refresh total cells for all related job rows
            window.grid.refreshCells({
                rowNodes: nodesToRefresh,
                columns: ['total'],
                force: true
            });
        } else {
            // Update only this row's total
            params.api.refreshCells({
                rowNodes: [params.node],
                columns: ['total'],
                force: true
            });
        }
        
        adjustGridHeight();
        debouncedAutosave();
    }
    
    // Function to create a new empty row
    function createNewRow() {
        return {
            job: '',
            description: '',
            quantity: 1,
            unit_cost: ''
        };
    }
    
    // Function to render delete icon
    function deleteIconCellRenderer() {
        return `<span class="delete-icon">🗑️</span>`;
    }
    
    // Function to create new row with shortcut
    function createNewRowShortcut(api) {
        // Add the new row
        const result = api.applyTransaction({
            add: [createNewRow()]
        });
        
        // Assert the row was added successfully
        console.assert(result && result.add && result.add.length === 1,
            'Failed to add new row');
        
        // Focus the first cell of the new row
        setTimeout(() => {
            const lastRowIndex = api.getDisplayedRowCount() - 1;
            api.setFocusedCell(lastRowIndex, 'job');
            adjustGridHeight();
        }, 100);
    }
    
    // Function to delete a row
    function deleteRow(api, node) {
        // Assert that api and node exist
        console.assert(api && node, 'API or node is undefined in deleteRow');
        
        // Only delete if there's more than one row
        if (api.getDisplayedRowCount() > 1) {
            // If the row has an ID, mark it for deletion on the server
            if (node.data.id && node.data.id !== 'tempId') {
                markLineItemAsDeleted(node.data.id);
            }
            
            // Delete the row and verify success
            const result = api.applyTransaction({ remove: [node.data] });
            console.assert(result && result.remove && result.remove.length === 1,
                'Failed to remove row');
                
            adjustGridHeight();
            debouncedAutosave();
        }
    }
    
    // Function to adjust grid height based on number of rows
    function adjustGridHeight() {
        const gridElement = document.getElementById('purchase-order-lines-grid');
        
        // Assert grid element exists
        console.assert(gridElement, "Grid container not found");
        if (!gridElement) return;

        // Count rows and calculate appropriate height
        let rowCount = 0;
        window.grid.forEachNode(() => rowCount++);
        
        const rowHeight = 40;
        const headerHeight = 50;
        const padding = 5;
        const minHeight = 150; // Minimum height for the grid
        
        // Set grid height
        const height = Math.max(rowCount * rowHeight + headerHeight + padding, minHeight);
        gridElement.style.height = `${height}px`;
    }
    
    // Removed saveOrder function as we're using autosave instead
    
    // Initial adjustment
    adjustGridHeight();
}); 