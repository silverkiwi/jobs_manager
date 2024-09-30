// This listner is for the entries towards the top.  The material and description fields, etc.
document.addEventListener('DOMContentLoaded', function () {
    const materialField = document.getElementById('materialGaugeQuantity');
    const descriptionField = document.getElementById('description');

    function autoExpand(field) {
        field.style.height = 'auto';  // Reset the height
        const newHeight = field.scrollHeight + 'px';  // Calculate the correct height based on content
        console.log('Auto expanding:', field.id, 'Setting height to:', newHeight);  // Debug: Log the new height
        field.style.height = newHeight;  // Apply the calculated height
    }

    materialField.addEventListener('input', function () {
        autoExpand(materialField);
    });

    descriptionField.addEventListener('input', function () {
        autoExpand(descriptionField);
    });

    // Initial expansion for preloaded content
    autoExpand(materialField);
    autoExpand(descriptionField);
});





// This listner is for the job pricing grid
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
        onCellValueChanged: function (event) {
            debouncedAutosaveData(event);  // Autosave on cell value change
        }
    };

    // Grid definitions for Time, Materials, and Adjustments
    const timeGridOptions = {
        ...commonGridOptions,
        onGridReady: function (params) {
            const section = params.context.section;
//            console.log(`Time grid API ready for ${section}`);
            window.grids[`${section}TimeTable`].gridApi = params.api;
        },
        columnDefs: [
            {headerName: 'Description', field: 'description', editable: true},
            {headerName: 'Items', field: 'items', editable: true, valueParser: numberParser},
            {headerName: 'Mins/Item', field: 'minsPerItem', editable: true, valueParser: numberParser},
            {headerName: 'Total Minutes', field: 'totalMinutes', valueGetter: calculateTotalMinutes, editable: false},
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
            {
                headerName: '',
                field: '',
                width: 40,
                cellRenderer: deleteIconCellRenderer,
                onCellClicked: onDeleteIconClicked
            }
        ],
        rowData: [{description: '', items: 0, minsPerItem: 0, totalMinutes: 0, rate: 0, total: 0}],  // Default 1 row
        context: {gridType: 'TimeTable'},

    };

    const materialsGridOptions = {
        ...commonGridOptions,
        onGridReady: function (params) {
            const section = params.context.section;
//            console.log(`Materials grid API ready for ${section}`);
            window.grids[`${section}MaterialsTable`].gridApi = params.api;
        },

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
            {
                headerName: '',
                field: '',
                width: 40,
                cellRenderer: deleteIconCellRenderer,
                onCellClicked: onDeleteIconClicked
            }
        ],
        rowData: [{itemCode: '', description: '', markup: 0, quantity: 0, rate: 0, total: 0, comments: ''}],  // Default 1 row
        context: {gridType: 'MaterialsTable'}
    };

    const adjustmentsGridOptions = {
        ...commonGridOptions,
        onGridReady: function (params) {
            const section = params.context.section;
//            console.log(`Adjustments grid API ready for ${section}`);
            window.grids[`${section}AdjustmentsTable`].gridApi = params.api;
        },
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
            {
                headerName: '',
                field: '',
                width: 40,
                cellRenderer: deleteIconCellRenderer,
                onCellClicked: onDeleteIconClicked
            }
        ],
        rowData: [{description: '', quantity: 0, amount: 0, total: 0, comments: ''}],  // Default 1 row
        context: {gridType: 'AdjustmentsTable'}
    };

    // Initialize AG Grids for Time, Materials, and Adjustments tables
    const sections = ['estimate', 'quote', 'reality'];
    window.grids = {}; // Initialize the grids object

    sections.forEach(section => {
        const timeGridElement = document.querySelector(`#${section}TimeTable`);
        const materialsGridElement = document.querySelector(`#${section}MaterialsTable`);
        const adjustmentsGridElement = document.querySelector(`#${section}AdjustmentsTable`);

        if (!timeGridElement || !materialsGridElement || !adjustmentsGridElement) {
            console.error(`Missing grid elements for section: ${section}`);
            return; // Skip this iteration if any element is missing
        }

        window.grids[`${section}TimeTable`] = {};  // Pre-initialize TimeTable entry
        window.grids[`${section}MaterialsTable`] = {};  // Pre-initialize MaterialsTable entry
        window.grids[`${section}AdjustmentsTable`] = {};  // Pre-initialize AdjustmentsTable entry

        // Create the grids
        agGrid.createGrid(timeGridElement, {
            ...timeGridOptions,
            context: {section, gridType: 'TimeTable'}
        });

        agGrid.createGrid(materialsGridElement, {
            ...materialsGridOptions,
            context: {section, gridType: 'MaterialsTable'}
        });

        agGrid.createGrid(adjustmentsGridElement, {
            ...adjustmentsGridOptions,
            context: {section, gridType: 'AdjustmentsTable'}
        });

    });

// Add a check after initialization to ensure all grids are created
    const expectedGridCount = sections.length * 3; // 3 grids per section
    if (Object.keys(window.grids).length !== expectedGridCount) {
        console.error('Not all grids were initialized. Application may not function correctly.');
        // You might want to add more robust error handling here, such as displaying an error message to the user
    }
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
            alert('Copy estimate feature coming soon!');
            console.log('Copying estimate to quote');
            // Implement the actual copying logic here
        });
    }

    // Submit Quote to Client (stub)
    const submitQuoteButton = document.getElementById('submitQuoteToClient');
    if (submitQuoteButton) {
        submitQuoteButton.addEventListener('click', function () {
            alert('Submit quote feature coming soon!');
            console.log('Submitting quote to client');
            // Implement the actual submission logic here
        });
    }

    const reviseQuoteButton = document.getElementById('reviseQuote');
    if (reviseQuoteButton) {
        reviseQuoteButton.addEventListener('click', function () {
            alert('Revise Quote feature coming soon!');
            console.log('Revise the quote');
            // Implement the actual submission logic here
        });
    }

    const invoiceJobButton = document.getElementById('invoiceJobButton');
    if (invoiceJobButton) {
        invoiceJobButton.addEventListener('click', function () {
            alert('Invoice Job feature coming soon!');
            console.log('Invoice Job');
            // Implement the actual invoice logic here
        });
    }

    const contactClientButton = document.getElementById('contactClientButton');
    if (contactClientButton) {
        contactClientButton.addEventListener('click', function () {
            alert('Contact Client feature coming soon!');
            console.log('Contact Client');
            // Implement the actual contact logic here
        });
    }



});
