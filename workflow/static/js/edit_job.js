document.addEventListener('DOMContentLoaded', function () {
    // Helper functions for currency formatting
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

    function createNewTimeRow() {
        return {
            description: '',
            items: 0,
            minsPerItem: 0,
            totalMinutes: 0,
            rate: 0,
            total: 0
        };
    }

    function createNewMaterialRow() {
        return {
            itemCode: '',
            description: '',
            markup: 0,
            quantity: 0,
            rate: 0,
            total: 0,
            comments: ''
        };
    }

    function createNewAdjustmentRow() {
        return {
            description: '',
            quantity: 0,
            amount: 0,
            total: 0,
            comments: ''
        };
    }

    // Grid options for Time table
    const timeGridOptions = {
        columnDefs: [
            {headerName: 'Description', field: 'description', editable: true},
            {headerName: 'Items', field: 'items', editable: true, valueParser: numberParser},
            {headerName: 'Mins/Item', field: 'minsPerItem', editable: true, valueParser: numberParser},
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
        ],
        rowData: [{description: '', items: 0, minsPerItem: 0, totalMinutes: 0, rate: 0, total: 0}],
        defaultColDef: {
            sortable: true,
            resizable: true
        },
        domLayout: 'autoHeight',
        rowHeight: 35,
        suppressPaginationPanel: true,
        onGridReady: params => {
            params.api.sizeColumnsToFit();
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        },
        enterMovesDown: true,
        enterMovesDownAfterEdit: true,
        stopEditingWhenCellsLoseFocus: true,
        onCellKeyDown: (params) => {
            if (params.event.key === 'Enter') {
                const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
                if (isLastRow) {
                    const newRow = createNewTimeRow(params.data);
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
    };

    // Grid options for Materials table
    const materialsGridOptions = {
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
        ],
        rowData: [{itemCode: '', description: '', markup: 0, quantity: 0, rate: 0, total: 0, comments: ''}],
        defaultColDef: {
            sortable: true,
            resizable: true
        },
        domLayout: 'autoHeight',
        rowHeight: 35,
        suppressPaginationPanel: true,
        onGridReady: params => {
            params.api.sizeColumnsToFit();
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        },
        enterMovesDown: true,
        enterMovesDownAfterEdit: true,
        stopEditingWhenCellsLoseFocus: true,
        onCellKeyDown: (params) => {
            if (params.event.key === 'Enter') {
                const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
                if (isLastRow) {
                    const newRow = createNewMaterialRow(params.data);
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

    };

    // Grid options for Adjustments table
    const adjustmentsGridOptions = {
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
        ],
        rowData: [{description: '', quantity: 0, amount: 0, total: 0, comments: ''}],
        defaultColDef: {
            sortable: true,
            resizable: true
        },
        domLayout: 'autoHeight',
        rowHeight: 35,
        suppressPaginationPanel: true,
        onGridReady: params => {
            params.api.sizeColumnsToFit();
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        },
        enterMovesDown: true,
        enterMovesDownAfterEdit: true,
        stopEditingWhenCellsLoseFocus: true,
        onCellKeyDown: (params) => {
            if (params.event.key === 'Enter') {
                const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
                if (isLastRow) {
                    const newRow = createNewAdjustmentRow(params.data);
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
    };

    // Define sections for the tables (estimate, quote, reality)
    const sections = ['estimate', 'quote', 'reality'];

    // Initialize AG Grid for each section
    sections.forEach(section => {
        const timeTableEl = document.querySelector(`#${section}TimeTable`);
        const materialsTableEl = document.querySelector(`#${section}MaterialsTable`);
        const adjustmentsTableEl = document.querySelector(`#${section}AdjustmentsTable`);

        if (timeTableEl) agGrid.createGrid(timeTableEl, timeGridOptions);
        if (materialsTableEl) agGrid.createGrid(materialsTableEl, materialsGridOptions);
        if (adjustmentsTableEl) agGrid.createGrid(adjustmentsTableEl, adjustmentsGridOptions);
    });

    // Totals Table initialization with valueGetters for dynamic totals calculation
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
        }
    };

    // Initialize Totals Table
    const totalsTableEl = document.querySelector('#totalsTable');
    if (totalsTableEl) {
        agGrid.createGrid(totalsTableEl, totalsGridOptions);
    }
});
