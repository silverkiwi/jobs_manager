document.addEventListener('DOMContentLoaded', function () {
    // Helper functions remain unchanged
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

    function createNewRow(gridType) {
        switch (gridType) {
            case 'time':
                return {description: '', items: 0, minsPerItem: 0, totalMinutes: 0, rate: 0, total: 0};
            case 'materials':
                return {itemCode: '', description: '', markup: 0, quantity: 0, rate: 0, total: 0, comments: ''};
            case 'adjustments':
                return {description: '', quantity: 0, amount: 0, total: 0, comments: ''};
            default:
                return {};
        }
    }

    const commonGridOptions = {
        rowHeight: 28,
        headerHeight: 32,
        suppressPaginationPanel: true,
        suppressHorizontalScroll: true,
        onGridReady: params => {
            params.api.sizeColumnsToFit();
            // Ensure the grid refreshes its size after initial render
            setTimeout(() => {
                params.api.resetRowHeights();
                params.api.onRowHeightChanged();
            }, 0);
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        },
        getRowHeight: () => 28, // Consistent row height
        enterNavigatesVertically: true,
        enterNavigatesVerticallyAfterEdit: true,
        stopEditingWhenCellsLoseFocus: true,
        onCellKeyDown: (params) => {
            if (params.event.key === 'Enter') {
                const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
                if (isLastRow) {
                    const newRow = createNewRow(params.context.gridType);
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
        },
        onCellMouseOver: (params) => {
            if (params.column.colId === 'delete') {
                const isLastRow = params.api.getDisplayedRowCount() === 1;
                params.event.target.style.cursor = isLastRow ? 'not-allowed' : 'pointer';
            }
        }
    };

    const deleteColumn = {
        headerName: '',
        field: 'delete',
        width: 40,
        cellRenderer: deleteIconCellRenderer,
        onCellClicked: onDeleteIconClicked,
        suppressSizeToFit: true
    };

    // Grid options for Time table
    const timeGridOptions = {
        ...commonGridOptions,
        columnDefs: [
            {
                headerName: 'Description',
                field: 'description',
                editable: params => params.context.section !== 'reality'
            },
            {
                headerName: 'Items',
                field: 'items',
                editable: params => params.context.section !== 'reality',
                valueParser: numberParser
            },
            {
                headerName: 'Mins/Item',
                field: 'minsPerItem',
                editable: params => params.context.section !== 'reality',
                valueParser: numberParser
            },
            {
                headerName: 'Total Minutes',
                field: 'totalMinutes',
                valueGetter: calculateTotalMinutes,
                editable: false,
                valueFormatter: currencyFormatter
            },
            {
                headerName: 'Rate',
                field: 'rate',
                editable: params => params.context.section !== 'reality',
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {
                headerName: 'Total',
                field: 'total',
                valueGetter: calculateTotal,
                editable: false,
                valueFormatter: currencyFormatter
            },
            deleteColumn
        ],
        rowData:
            [{description: '', items: 0, minsPerItem: 0, totalMinutes: 0, rate: 0, total: 0}],
        context: {gridType: 'time'}
    };

// Grid options for Materials table
    const materialsGridOptions = {
        ...commonGridOptions,
        columnDefs: [
            {headerName: 'Item Code', field: 'itemCode', editable: true},
            {headerName: 'Description', field: 'description', editable: true},
            {headerName: 'Markup %', field: 'markup', editable: true, valueParser: numberParser},
            {headerName: 'Quantity', field: 'quantity', editable: true, valueParser: numberParser},
            {
                headerName: 'Rate',
                field: 'rate',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {
                headerName: 'Total',
                field: 'total',
                valueGetter: calculateTotal,
                editable: false,
                valueFormatter: currencyFormatter
            },
            {headerName: 'Comments', field: 'comments', editable: true},
            deleteColumn
        ],
        rowData: [{itemCode: '', description: '', markup: 0, quantity: 0, rate: 0, total: 0, comments: ''}],
        context: {gridType: 'materials'}
    };

// Grid options for Adjustments table
    const adjustmentsGridOptions = {
        ...commonGridOptions,
        columnDefs: [
            {headerName: 'Description', field: 'description', editable: true},
            {headerName: 'Quantity', field: 'quantity', editable: true, valueParser: numberParser},
            {
                headerName: 'Amount',
                field: 'amount',
                editable: true,
                valueParser: numberParser,
                valueFormatter: currencyFormatter
            },
            {
                headerName: 'Total',
                field: 'total',
                valueGetter: calculateTotal,
                editable: false,
                valueFormatter: currencyFormatter
            },
            {headerName: 'Comments', field: 'comments', editable: true},
            deleteColumn
        ],
        rowData: [{description: '', quantity: 0, amount: 0, total: 0, comments: ''}],
        context: {gridType: 'adjustments'}
    };

// Define sections for the tables (estimate, quote, reality)
    const sections = ['estimate', 'quote', 'reality'];

// Initialize AG Grid for each section
    sections.forEach(section => {
        const timeTableEl = document.querySelector(`#${section}TimeTable`);
        const materialsTableEl = document.querySelector(`#${section}MaterialsTable`);
        const adjustmentsTableEl = document.querySelector(`#${section}AdjustmentsTable`);

        agGrid.createGrid(timeTableEl, timeGridOptions);
        agGrid.createGrid(materialsTableEl, materialsGridOptions);
        agGrid.createGrid(adjustmentsTableEl, adjustmentsGridOptions);
    });

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
        ],
        defaultColDef: {
            sortable: true,
            resizable: true
        },
        domLayout: 'autoHeight',
        rowHeight: 28,
        headerHeight: 32,
        suppressPaginationPanel: true,
        suppressHorizontalScroll: true,
        onGridReady: params => {
            params.api.sizeColumnsToFit();
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
})


// Next section is for the buttons

document.addEventListener('DOMContentLoaded', function () {
    // Copy Estimate to Quote functionality
    document.getElementById('copyEstimateToQuote').addEventListener('click', function () {
        // Implement the copy logic here
        console.log('Copying estimate to quote');
        // You'll need to implement the actual copying logic
    });

    // Submit Quote to Client functionality
    document.getElementById('submitQuoteToClient').addEventListener('click', function () {
        // Implement the submit logic here
        console.log('Submitting quote to client');
        // You'll need to implement the actual submission logic
    });

});
