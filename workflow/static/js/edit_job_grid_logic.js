document.addEventListener('DOMContentLoaded', function () {
    // Helper functions for grid calculations
    function currencyFormatter(params) {
        return '$' + params.value.toFixed(2);
    }

    function numberParser(params) {
        return Number(params.newValue);
    }

    function calculateTotal(params) {
        return params.data.items * params.data.rate;
    }

    function calculateTotalMinutes(params) {
        return params.data.items * params.data.minsPerItem;
    }

    function deleteIconCellRenderer(params) {
        const isLastRow = params.api.getDisplayedRowCount() === 1;
        const iconClass = isLastRow ? 'delete-icon disabled' : 'delete-icon';
        return `<span class="${iconClass}">🗑️</span>`;
    }

    function onDeleteIconClicked(params) {
        if (params.api.getDisplayedRowCount() > 1) {
            params.api.applyTransaction({remove: [params.node.data]});
        }
    }

    // Row creation on "Enter" key if on the last row
    function createNewRow(gridType) {
        if (gridType === 'TimeTable') {
            return {description: '', items: 0, minsPerItem: 0, totalMinutes: 0, rate: 0, total: 0};
        } else if (gridType === 'MaterialsTable') {
            return {itemCode: '', description: '', markup: 0, quantity: 0, rate: 0, total: 0, comments: ''};
        } else if (gridType === 'AdjustmentsTable') {
            return {description: '', quantity: 0, amount: 0, total: 0, comments: ''};
        }
        return null;
    }

    function onCellKeyDown(params) {
        if (params.event.key === 'Enter') {
            const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
            if (isLastRow) {
                const newRow = createNewRow(params.context.gridType);
                if (newRow) {
                    params.api.applyTransaction({add: [newRow]});
                    setTimeout(() => {
                        params.api.setFocusedCell(params.rowIndex + 1, params.column.colId);
                        params.api.startEditingCell({
                            rowIndex: params.rowIndex + 1,
                            colKey: params.column.colId
                        });
                    }, 0);
                }
            }
        }
    }

    // Grid options for Time, Materials, and Adjustments tables (default 1 row, fixed height)
    const commonGridOptions = {
        rowHeight: 28,  // Consistent row height
        headerHeight: 32,  // Consistent header height
        suppressPaginationPanel: true,
        suppressHorizontalScroll: true,
        defaultColDef: {
            sortable: true,
            resizable: true  // Allow columns to be resized
        },
        // Removed `domLayout: 'autoHeight'` for these tables
        onGridReady: params => {
            params.api.sizeColumnsToFit();  // Resize columns to fit the grid width
            setTimeout(() => {
                params.api.resetRowHeights();  // Ensure row heights are consistent
            }, 0);
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();  // Adjust column sizes when the grid size changes
        },
        enterNavigatesVertically: true,
        enterNavigatesVerticallyAfterEdit: true,
        stopEditingWhenCellsLoseFocus: true,
        onCellKeyDown: onCellKeyDown,  // Handle Enter key for row creation
        onCellValueChanged: function(event) {
            debouncedAutosaveGridData(event);  // Autosave on cell value change
        }
    };

    // Grid definitions for Time, Materials, and Adjustments
    const timeGridOptions = {
        ...commonGridOptions,
        columnDefs: [
            {headerName: 'Description', field: 'description', editable: true},
            {headerName: 'Items', field: 'items', editable: true, valueParser: numberParser},
            {headerName: 'Mins/Item', field: 'minsPerItem', editable: true, valueParser: numberParser},
            {headerName: 'Total Minutes', field: 'totalMinutes', valueGetter: calculateTotalMinutes, editable: false},
            {headerName: 'Rate', field: 'rate', editable: true, valueParser: numberParser, valueFormatter: currencyFormatter},
            {headerName: 'Total', field: 'total', valueGetter: calculateTotal, editable: false, valueFormatter: currencyFormatter},
            {headerName: '', field: '', width: 40, cellRenderer: deleteIconCellRenderer, onCellClicked: onDeleteIconClicked}
        ],
        rowData: [{description: '', items: 0, minsPerItem: 0, totalMinutes: 0, rate: 0, total: 0}],  // Default 1 row
        context: {gridType: 'TimeTable'}
    };

    const materialsGridOptions = {
        ...commonGridOptions,
        columnDefs: [
            {headerName: 'Item Code', field: 'itemCode', editable: true},
            {headerName: 'Description', field: 'description', editable: true},
            {headerName: 'Markup %', field: 'markup', editable: true, valueParser: numberParser},
            {headerName: 'Quantity', field: 'quantity', editable: true, valueParser: numberParser},
            {headerName: 'Rate', field: 'rate', editable: true, valueParser: numberParser, valueFormatter: currencyFormatter},
            {headerName: 'Total', field: 'total', valueGetter: calculateTotal, editable: false, valueFormatter: currencyFormatter},
            {headerName: 'Comments', field: 'comments', editable: true},
            {headerName: '', field: '', width: 40, cellRenderer: deleteIconCellRenderer, onCellClicked: onDeleteIconClicked}
        ],
        rowData: [{itemCode: '', description: '', markup: 0, quantity: 0, rate: 0, total: 0, comments: ''}],  // Default 1 row
        context: {gridType: 'MaterialsTable'}
    };

    const adjustmentsGridOptions = {
        ...commonGridOptions,
        columnDefs: [
            {headerName: 'Description', field: 'description', editable: true},
            {headerName: 'Quantity', field: 'quantity', editable: true, valueParser: numberParser},
            {headerName: 'Amount', field: 'amount', editable: true, valueParser: numberParser, valueFormatter: currencyFormatter},
            {headerName: 'Total', field: 'total', valueGetter: calculateTotal, editable: false, valueFormatter: currencyFormatter},
            {headerName: 'Comments', field: 'comments', editable: true},
            {headerName: '', field: '', width: 40, cellRenderer: deleteIconCellRenderer, onCellClicked: onDeleteIconClicked}
        ],
        rowData: [{description: '', quantity: 0, amount: 0, total: 0, comments: ''}],  // Default 1 row
        context: {gridType: 'AdjustmentsTable'}
    };

    // Initialize AG Grids for Time, Materials, and Adjustments tables
    const sections = ['estimate', 'quote', 'reality'];
    sections.forEach(section => {
        agGrid.createGrid(document.querySelector(`#${section}TimeTable`), timeGridOptions);
        agGrid.createGrid(document.querySelector(`#${section}MaterialsTable`), materialsGridOptions);
        agGrid.createGrid(document.querySelector(`#${section}AdjustmentsTable`), adjustmentsGridOptions);
    });

    // Grid options for Totals table (default 4 rows, autoHeight for proper resizing)
    const totalsGridOptions = {
        columnDefs: [
            {headerName: 'Category', field: 'category', editable: false},
            {headerName: 'Estimate', field: 'estimate', editable: false, valueFormatter: currencyFormatter},
            {headerName: 'Quote', field: 'quote', editable: false, valueFormatter: currencyFormatter},
            {headerName: 'Reality', field: 'reality', editable: false, valueFormatter: currencyFormatter},
        ],
        rowData: [
            {category: 'Total Labour', estimate: 0, quote: 0, reality: 0},
            {category: 'Total Materials', estimate: 0, quote: 0, reality: 0},
            {category: 'Total Adjustments', estimate: 0, quote: 0, reality: 0},
            {category: 'Total Project Cost', estimate: 0, quote: 0, reality: 0}
        ],  // Default 4 rows
        domLayout: 'autoHeight',  // Ensure table height adjusts automatically
        rowHeight: 28,
        headerHeight: 32,
        suppressPaginationPanel: true,
        suppressHorizontalScroll: true,
        onGridReady: params => {
            params.api.sizeColumnsToFit();  // Resize columns to fit the table
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        }
    };

    // Initialize Totals Table
    const totalsTableEl = document.querySelector('#totalsTable');
    if (totalsTableEl) {
        agGrid.createGrid(totalsTableEl, totalsGridOptions);
    }

    // Copy Estimate to Quote (stub)
    const copyEstimateButton = document.getElementById('copyEstimateToQuote');
    if (copyEstimateButton) {
        copyEstimateButton.addEventListener('click', function () {
            console.log('Copying estimate to quote');
            // Implement the actual copying logic here
        });
    }

    // Submit Quote to Client (stub)
    const submitQuoteButton = document.getElementById('submitQuoteToClient');
    if (submitQuoteButton) {
        submitQuoteButton.addEventListener('click', function () {
            console.log('Submitting quote to client');
            // Implement the actual submission logic here
        });
    }
});
