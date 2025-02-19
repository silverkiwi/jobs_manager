import { numberParser, currencyFormatter } from "./parsers.js";
import { 
    calculateGridHeight,
    onCellKeyDown, 
    calculateRetailRate, 
    getRetailRate, 
    setRetailRate,
    calculateTotalCost,
    calculateTotalRevenue
} from "./grid_utils.js";

import { debouncedAutosave } from "../edit_job_form_autosave.js";

export function createCommonGridOptions() {
    return {
        rowHeight: 28,
        headerHeight: 32,
        domLayout: 'autoHeight',
        suppressPaginationPanel: true,
        suppressHorizontalScroll: true,
        defaultColDef: {
            sortable: true,
            resizable: true,
        },
        onGridReady: function (params) {
            // Store the grid API in the global window.grids object for easy access
            const gridKey = params.context.gridKey;  // Using the context to uniquely identify the grid
            const gridElement = document.querySelector(`#${gridKey}`);
            const initialNumRows = 1; // Default initial number of rows
            const initialGridHeight = calculateGridHeight(params.api, initialNumRows);
            gridElement.style.height = `${initialGridHeight}px`;

            window.grids[gridKey] = { api: params.api };

            params.api.sizeColumnsToFit();
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        },
        autoSizeStrategy: {
            type: 'fitCellContents'
        },
        enterNavigatesVertically: true,
        enterNavigatesVerticallyAfterEdit: true,
        stopEditingWhenCellsLoseFocus: true,
        tabToNextCell: (params) => {
            const allColumns = params.api.getAllDisplayedColumns();

            // Filter only "leaf columns" (real cells) - i.e., those that don't have children
            const displayedColumns = allColumns.filter(col => !col.getColDef().children);

            const rowCount = params.api.getDisplayedRowCount();
            let { rowIndex, column, floating } = params.previousCellPosition;

            // If focus came from header, force start at first body row
            if (floating) {
                rowIndex = 0;
            }

            // Find current column index within filtered array
            let currentColIndex = displayedColumns.findIndex(col => col.getColId() === column.getColId());
            if (currentColIndex === -1) return null;

            let nextColIndex = currentColIndex;
            let nextRowIndex = rowIndex;

            // Total number of cells to avoid infinite loop
            const totalCells = rowCount * displayedColumns.length;
            let count = 0;

            // Helper function to test if a cell is editable,
            // providing expected parameters for isCellEditable
            function isEditable(rowIndex, colIndex) {
                // Get rowNode for current row (assuming client-side rowModel)
                const rowNode = params.api.getDisplayedRowAtIndex(rowIndex);
                const col = displayedColumns[colIndex];

                // Build parameters object for isCellEditable
                const cellParams = {
                    node: rowNode,
                    column: col,
                    colDef: col.getColDef(),
                    rowIndex: rowIndex,
                    data: rowNode ? rowNode.data : null,
                    api: params.api,
                    context: params.context
                };

                return col.isCellEditable(cellParams);
            }

            // Search for next editable column
            do {
                nextColIndex++; // Advance to next column
                if (nextColIndex >= displayedColumns.length) {
                    // If past last column, return to first and advance row
                    nextColIndex = 0;
                    nextRowIndex++;
                    // If we reached end of rows, return null to avoid invalid index
                    if (nextRowIndex >= rowCount) {
                        return null;
                    }
                }
                count++;
                if (count > totalCells) {
                    return null; // Avoid infinite loop if no cell is editable
                }
            } while (!isEditable(nextRowIndex, nextColIndex));

            // Ensure row is visible (automatic scroll)
            params.api.ensureIndexVisible(nextRowIndex);

            return {
                rowIndex: nextRowIndex,
                column: displayedColumns[nextColIndex],
                floating: null
            };
        },
        onCellKeyDown: onCellKeyDown,
        onRowDataUpdated: function (params) {  // Handles row updates
            const gridKey = params.context.gridKey;
            const gridElement = document.querySelector(`#${gridKey}`);
            const rowCount = params.api.getDisplayedRowCount();
            const newHeight = calculateGridHeight(params.api, rowCount);
            // console.log(`Grid Key: ${gridKey}, Updated Grid Height: ${newHeight}`);
            gridElement.style.height = `${newHeight}px`;
        },

        onCellValueChanged: function (event) {
            const gridType = event.context.gridType;
            const data = event.data;

            if (gridType === 'TimeTable') {
                if (['mins_per_item', 'items'].includes(event.column.colId)) {
                    const totalMinutes = event.data.items * event.data.mins_per_item;
                    const hours = (totalMinutes / 60).toFixed(1);
                    event.data.total_minutes = `${totalMinutes} (${hours} hours)`;
                    event.api.refreshCells({ rowNodes: [event.node], columns: ['total_minutes'], force: true });
                }
            } else if (gridType === 'MaterialsTable') {
                if (event.column.colId === 'unit_cost') {
                    fetchMaterialsMarkup(data).then(markupRate => {
                        data.unit_revenue = calculateRetailRate(data.unit_cost, markupRate);
                        event.api.refreshCells({ rowNodes: [event.node], columns: ['unit_revenue'], force: true });
                    });
                }

                data.revenue = (data.quantity || 0) * (data.unit_revenue || 0);
                event.api.refreshCells({ rowNodes: [event.node], columns: ['revenue'], force: true });
            }

            event.api.refreshCells({ rowNodes: [event.node], columns: ['revenue', 'total_minutes'], force: true });

            debouncedAutosave(event);
            calculateTotalRevenue();
            calculateTotalCost();

        },
    };
}

// Advanced grids
export function createAdvancedTimeGridOptions(commonGridOptions, trashCanColumn) {
    return {
        ...commonGridOptions,
        columnDefs: [
            {
                headerName: 'Description',
                field: 'description',
                editable: true,
                flex: 2,
                minWidth: 100,
                cellRenderer: (params) => {
                    return `<span>${params.value || 'No Description'}</span>`;
                }
            },
            {
                headerName: 'Timesheet',
                field: 'link',
                width: 120,
                minWidth: 100,
                cellRenderer: (params) => {
                    if (params.data.link && params.data.link.trim()) {
                        const linkLabel =
                            params.data.link === '/timesheets/overview/'
                                ? ''
                                : 'View Timesheet';

                        if (linkLabel === '') {
                            return `<span class="text-warning">Not found for this entry.</span>`;
                        }
                        return `<a href='${params.data.link}' target='_blank' class='action-link'>${linkLabel}</a>`;
                    }
                    return 'Not found for this entry.';
                }
            },
            {
                headerName: 'Items',
                field: 'items',
                editable: true,
                valueParser: numberParser,
                minWidth: 80,
                flex: 1
            },
            {
                headerName: 'Mins/Item',
                field: 'mins_per_item',
                editable: true,
                valueParser: numberParser,
                minWidth: 90,
                flex: 1
            },
            {
                headerName: 'Total Minutes',
                field: 'total_minutes',
                editable: false,
                valueFormatter: (params) => {
                    if (params.value !== undefined && params.value !== null) {
                        const totalMinutes = parseFloat(params.value) || 0;
                        const decimalHours = (totalMinutes / 60).toFixed(1);
                        return `${totalMinutes} (${decimalHours} hours)`;
                    }
                    return '0 (0.0 hours)';
                },
                valueParser: (params) => {
                    return parseFloat(params.newValue) || 0;
                },
            },
            {
                headerName: 'Wage Rate',
                field: 'wage_rate',
                editable: false,
                hide: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter,
                minWidth: 100,
                flex: 1
            },
            {
                headerName: 'Charge Rate',
                field: 'charge_out_rate',
                editable: false,
                hide: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter,
                minWidth: 100,
                flex: 1
            },

            {
                ...trashCanColumn,
                minWidth: 40,
                maxWidth: 40
            }
        ],
        rowData: [],
        context: { gridType: 'TimeTable' },
    };
}

export function createAdvancedMaterialsGridOptions(commonGridOptions, trashCanColumn) {
    return {
        ...commonGridOptions,
        columnDefs: [
            { headerName: 'Item Code', field: 'item_code', editable: false, hide: true },
            { headerName: 'Description', field: 'description', editable: true, flex: 2 },
            { headerName: 'Quantity', field: 'quantity', editable: true, valueParser: numberParser },
            {
                headerName: 'Cost Rate',
                field: 'unit_cost',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {
                headerName: 'Retail Rate',
                field: 'unit_revenue',
                editable: true,
                valueGetter: getRetailRate,
                valueSetter: setRetailRate,
                valueFormatter: currencyFormatter,
            },
            { headerName: 'Revenue', field: 'revenue', editable: false, valueFormatter: currencyFormatter },
            { headerName: 'Comments', field: 'comments', editable: true, flex: 2 },
            trashCanColumn,
        ],
        rowData: [],
        context: { gridType: 'MaterialsTable' }
    };
}

export function createAdvancedAdjustmentsGridOptions(commonGridOptions, trashCanColumn) {
    return {
        ...commonGridOptions,
        columnDefs: [
            { headerName: 'Description', field: 'description', editable: true, flex: 2 },
            {
                headerName: 'Cost Adjustment',
                field: 'cost_adjustment',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {
                headerName: 'Price Adjustment',
                field: 'price_adjustment',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            { headerName: 'Comments', field: 'comments', editable: true, flex: 2 },
            trashCanColumn,
        ],
        rowData: [],
        context: { gridType: 'AdjustmentTable' }
    };
}

// Simple grids
export function createSimpleTimeGridOptions(commonGridOptions, trashCanColumn) {
    return {
        ...commonGridOptions,
        columnDefs: [
            {
                headerName: 'Description',
                field: 'description',
                editable: true,
                hide: true,
                flex: 2
            },
            {
                headerName: 'Hours',
                field: 'hours',
                editable: true,
                valueParser: numberParser,
                minWidth: 80
            },
            {
                headerName: 'Cost of Time ($)',
                field: 'cost_of_time',
                editable: false,
                valueParser: numberParser,
                valueFormatter: currencyFormatter,
                minWidth: 80
            },
            {
                headerName: 'Value of Time ($)',
                field: 'value_of_time',
                editable: false,
                valueParser: numberParser,
                valueFormatter: currencyFormatter,
                minWidth: 80
            },
            trashCanColumn
        ],
        rowData: [
            { 'description': 'Single time entry', 'hours': 0 },
        ],
        context: { gridType: 'SimpleTimeTable' }
    };
}

export function createSimpleMaterialsGridOptions(commonGridOptions, trashCanColumn) {
    return {
        ...commonGridOptions,
        columnDefs: [
            {
                headerName: 'Material Description',
                field: 'description',
                editable: true,
                hide: true,
                flex: 2
            },
            {
                headerName: 'Cost ($)',
                field: 'material_cost',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter,
                minWidth: 80
            },
            {
                headerName: 'Retail Price ($)',
                field: 'retail_price',
                editable: true,
                valueParser: numberParser,
                minWidth: 80
            },
            trashCanColumn
        ],
        rowData: [
            { 'description': 'Single materials entry', 'material_cost': 0, 'retail_price': 0 },
        ],
        context: { gridType: 'SimpleMaterialsTable' }
    };
}

export function createSimpleAdjustmentsGridOptions(commonGridOptions, trashCanColumn) {
    return {
        ...commonGridOptions,
        columnDefs: [
            {
                headerName: 'Adjustment Description',
                field: 'description',
                editable: true,
                hide: true,
                flex: 2
            },
            {
                headerName: 'Cost ($)',
                field: 'cost_adjustment',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter,
                minWidth: 80
            },
            {
                headerName: 'Retail ($)',
                field: 'price_adjustment',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter,
                minWidth: 80
            },
            trashCanColumn
        ],
        rowData: [
            { 'description': 'Single adjustment entry', 'cost_adjustment': 0, 'price_adjustment': 0 },
        ],
        context: { gridType: 'SimpleAdjustmentsTable' }
    };
}

export function createSimpleTotalsGridOptions(commonGridOptions, trashCanColumn) {
    return {
        ...commonGridOptions,
        columnDefs: [
            {
                headerName: 'Total Cost ($)',
                field: 'cost',
                editable: false,
                valueParser: numberParser,
                valueFormatter: currencyFormatter,
                minWidth: 80
            },
            {
                headerName: 'Total Retail ($)',
                field: 'retail',
                editable: false,
                valueParser: numberParser,
                valueFormatter: currencyFormatter,
                minWidth: 80
            },
            trashCanColumn
        ],
        rowData: [
            { 'cost': 0, 'retail': 0 },
        ],
        context: { gridType: 'SimpleTotalTable' }
    };
}