import { calculateTotalRevenue, calculateTotalCost } from "./grid_utils.js";
import { currencyFormatter } from "./parsers.js";

// Grid options for Totals table (default 4 rows, autoHeight for proper resizing)
export function createRevenueGridOptions() {
    return {
        columnDefs: [
            { headerName: 'Category', field: 'category', editable: false },
            { headerName: 'Estimate', field: 'estimate', editable: false, valueFormatter: currencyFormatter },
            { headerName: 'Quote', field: 'quote', editable: false, valueFormatter: currencyFormatter },
            { headerName: 'Reality', field: 'reality', editable: false, valueFormatter: currencyFormatter },
        ],
        rowData: [
            { category: 'Total Time', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Materials', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Adjustments', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Project Revenue', estimate: 0, quote: 0, reality: 0 }
        ],  // Default 4 rows
        domLayout: 'autoHeight',
        rowHeight: 28,
        headerHeight: 32,
        suppressPaginationPanel: true,
        suppressHorizontalScroll: true,
        onGridReady: params => {
            window.grids['revenueTable'] = { gridInstance: params.api, api: params.api };
            params.api.sizeColumnsToFit();

            calculateTotalRevenue();
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        },
        autoSizeStrategy: {
            type: 'fitCellContents'
        }
    };
}

export function createCostGridOptions() {
    return {
        columnDefs: [
            { headerName: 'Category', field: 'category', editable: false },
            { headerName: 'Estimate', field: 'estimate', editable: false, valueFormatter: currencyFormatter },
            { headerName: 'Quote', field: 'quote', editable: false, valueFormatter: currencyFormatter },
            { headerName: 'Reality', field: 'reality', editable: false, valueFormatter: currencyFormatter },
        ],
        rowData: [
            { category: 'Total Time', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Materials', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Adjustments', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Project Cost', estimate: 0, quote: 0, reality: 0 }
        ],  // Default 4 rows
        domLayout: 'autoHeight',
        rowHeight: 28,
        headerHeight: 32,
        suppressPaginationPanel: true,
        suppressHorizontalScroll: true,
        onGridReady: params => {
            window.grids['costsTable'] = { gridInstance: params.api, api: params.api };
            params.api.sizeColumnsToFit();

            calculateTotalCost();
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        },
        autoSizeStrategy: {
            type: 'fitCellContents'
        }
    };
}