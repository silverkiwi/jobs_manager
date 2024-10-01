// This listner is for the entries towards the top.  The material and description fields, etc.
document.addEventListener('DOMContentLoaded', function () {
    const materialField = document.getElementById('materialGaugeQuantity');
    const descriptionField = document.getElementById('description');

    function autoExpand(field) {
        // Reset field height
        field.style.height = 'inherit';

        // Get the computed styles for the element
        const computed = window.getComputedStyle(field);

        // Calculate the height
        const height = parseInt(computed.getPropertyValue('border-top-width'), 10)
            + parseInt(computed.getPropertyValue('padding-top'), 10)
            + field.scrollHeight
            + parseInt(computed.getPropertyValue('padding-bottom'), 10)
            + parseInt(computed.getPropertyValue('border-bottom-width'), 10);

        field.style.height = `${height}px`;
    }

    function addAutoExpand(field) {
        field.addEventListener('input', function () {
            autoExpand(field);
        });
        // Expand on initial load
        autoExpand(field);
    }

    if (materialField) addAutoExpand(materialField);
    if (descriptionField) addAutoExpand(descriptionField);
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
        const gridType = params.context.gridType;
        if (gridType === 'TimeTable') {
            return (params.data.items || 0) * (params.data.rate || 0);
        } else if (gridType === 'MaterialsTable') {
            return (params.data.quantity || 0) * (params.data.rate || 0);
        } else if (gridType === 'AdjustmentsTable') {
            return (params.data.quantity || 0) * (params.data.amount || 0);
        }
        console.log("calculate total not time, material or adjustment");
        return 0;
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

    function createDefaultRowData(gridType) {
        if (gridType === 'Time') {
            return [{description: '', items: 0, minsPerItem: 0, totalMinutes: 0, rate: 0, total: 0}];
        } else if (gridType === 'Materials') {
            return [{itemCode: '', description: '', markup: 0, quantity: 0, rate: 0, total: 0, comments: ''}];
        } else if (gridType === 'Adjustments') {
            return [{description: '', quantity: 0, amount: 0, total: 0, comments: ''}];
        }
        return [];
    }

    // Function to calculate totals
    function calculateTotals() {
        console.log('Calculating totals...');
        console.log('Available grids:', Object.keys(window.grids));

        const totals = {
            time: {estimate: 0, quote: 0, reality: 0},
            materials: {estimate: 0, quote: 0, reality: 0},
            adjustments: {estimate: 0, quote: 0, reality: 0}
        };
        const sections = ['estimate', 'quote', 'reality'];
        const workTypes = ['Time', 'Materials', 'Adjustments'];

        sections.forEach(section => {
            console.log(`Calculating totals for ${section}...`);

            workTypes.forEach(gridType => {
                const gridKey = `${section}${gridType}Table`;
                const gridData = window.grids[gridKey];
                console.log(`Checking grid for ${gridKey}:`, gridData);

                if (gridData && gridData.api) {
                    gridData.api.forEachNode(node => {
                        const total = parseFloat(node.data.total) || 0;
                        const totalType = gridType.toLowerCase();
                        if (totals[totalType] && totals[totalType][section] !== undefined) {
                            totals[totalType][section] += total;
                            console.log(`${gridKey}: Row data:`, node.data, `Total:`, total, `Added to:`, totalType, section);
                        } else {
                            console.warn(`Invalid total type or section: ${totalType}, ${section}`);
                        }
                    });
                } else {
                    console.warn(`Grid or API not found for ${gridKey}. Grid data:`, gridData);
                }
            });

            console.log(`${section} totals:`, {
                time: totals.time[section],
                materials: totals.materials[section],
                adjustments: totals.adjustments[section]
            });
        });

        console.log('Final totals:', totals);

        // Update the totals table
        const totalsGrid = window.grids['totalsTable'];
        if (totalsGrid) {
            if (totalsGrid.api) {
                totalsGrid.api.forEachNode((node, index) => {
                    const data = node.data;
                    switch (index) {
                        case 0: // Total Time
                            data.estimate = totals.time.estimate;
                            data.quote = totals.time.quote;
                            data.reality = totals.time.reality;
                            break;
                        case 1: // Total Materials
                            data.estimate = totals.materials.estimate;
                            data.quote = totals.materials.quote;
                            data.reality = totals.materials.reality;
                            break;
                        case 2: // Total Adjustments
                            data.estimate = totals.adjustments.estimate;
                            data.quote = totals.adjustments.quote;
                            data.reality = totals.adjustments.reality;
                            break;
                        case 3: // Total Project Cost
                            data.estimate = totals.time.estimate + totals.materials.estimate + totals.adjustments.estimate;
                            data.quote = totals.time.quote + totals.materials.quote + totals.adjustments.quote;
                            data.reality = totals.time.reality + totals.materials.reality + totals.adjustments.reality;
                            break;
                    }
                    console.log(`Updating totals row ${index}:`, data);
                });
                totalsGrid.api.refreshCells();
                console.log('Totals table updated');
            } else {
                console.warn('Totals grid API not found');
            }
        } else {
            console.warn('Totals grid not found');
        }
    }

    // Grid options for Time, Materials, and Adjustments tables (default 1 row, fixed height)
    const commonGridOptions = {
        rowHeight: 28,
        headerHeight: 32,
        suppressPaginationPanel: true,
        suppressHorizontalScroll: true,
        defaultColDef: {
            sortable: true,
            resizable: true
        },
        onGridReady: function (params) {
            params.api.sizeColumnsToFit();
            setTimeout(() => {
                params.api.resetRowHeights();
            }, 0);

            const gridKey = params.context.gridKey;
            window.grids[gridKey] = {gridInstance: params.api, api: params.api};
            console.log(`Grid API ready for ${gridKey}:`, params.api);
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        },
        enterNavigatesVertically: true,
        enterNavigatesVerticallyAfterEdit: true,
        stopEditingWhenCellsLoseFocus: true,
        onCellKeyDown: onCellKeyDown,
        onCellValueChanged: function (event) {
            console.log('Cell value changed:', event);
            const gridType = event.context.gridType;
            const data = event.data;
            if (gridType === 'TimeTable') {
                data.totalMinutes = (data.items || 0) * (data.minsPerItem || 0);
                data.total = (data.items || 0) * (data.rate || 0);
            } else if (gridType === 'MaterialsTable') {
                data.total = (data.quantity || 0) * (data.rate || 0);
            } else if (gridType === 'AdjustmentsTable') {
                data.total = (data.quantity || 0) * (data.amount || 0);
            }
            // Refresh the cells that depend on the data
            event.api.refreshCells({rowNodes: [event.node], columns: ['total', 'totalMinutes'], force: true});
            debouncedAutosaveData(event);
            calculateTotals();
        }
    };


    // Grid definitions for Time, Materials, and Adjustments
    const timeGridOptions = {
        ...commonGridOptions,
        columnDefs: [
            {headerName: 'Description', field: 'description', editable: true},
            {headerName: 'Items', field: 'items', editable: true, valueParser: numberParser},
            {headerName: 'Mins/Item', field: 'minsPerItem', editable: true, valueParser: numberParser},
            {headerName: 'Total Minutes', field: 'totalMinutes', editable: false},
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
    const workType = ['Time', 'Materials', 'Adjustments'];
    window.grids = {}; // Initialize the grids object

    sections.forEach(section => {
        workType.forEach(gridType => {
            const gridKey = `${section}${gridType}Table`;
            const gridElement = document.querySelector(`#${gridKey}`);

            if (!gridElement) {
                console.error(`Grid element not found for ${gridKey}`);
                return;
            }

            let specificGridOptions;

            switch (gridType) {
                case 'Time':
                    specificGridOptions = timeGridOptions;
                    break;
                case 'Materials':
                    specificGridOptions = materialsGridOptions;
                    break;
                case 'Adjustments':
                    specificGridOptions = adjustmentsGridOptions;
                    break;
            }

            // Create default row data based on grid type
            const rowData = createDefaultRowData(gridType);

            // Build grid options for each grid instance
            const gridOptions = {
                ...commonGridOptions,
                ...specificGridOptions,
                context: {section, gridType: `${gridType}Table`, gridKey: gridKey},
                rowData: rowData,
            };

            try {
                const gridInstance = agGrid.createGrid(gridElement, gridOptions);
                console.log(`Grid initialized for ${gridKey}:`, gridInstance);
            } catch (error) {
                console.error(`Error initializing grid for ${gridKey}:`, error);
            }
        });
    });

    // Add a check after initialization to ensure all grids are created
    const expectedGridCount = sections.length * 3; // 3 grids per section
    const actualGridCount = Object.keys(window.grids).length;
    console.log(`Expected grid count: ${expectedGridCount}, Actual grid count: ${actualGridCount}`);
    if (actualGridCount !== expectedGridCount) {
        console.error(`Not all grids were initialized. Expected: ${expectedGridCount}, Actual: ${actualGridCount}`);
        console.error('Initialized grids:', Object.keys(window.grids));
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
            {category: 'Total Time', estimate: 0, quote: 0, reality: 0},
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
            window.grids['totalsTable'] = {gridInstance: params.api, api: params.api};
            console.log('Totals grid ready:', window.grids['totalsTable']);
            params.api.sizeColumnsToFit();
        },
        onGridSizeChanged: params => {
            params.api.sizeColumnsToFit();
        }
    };

    // Initialize Totals Table
    const totalsTableEl = document.querySelector('#totalsTable');
    if (totalsTableEl) {
        try {
            const totalsGrid = agGrid.createGrid(totalsTableEl, totalsGridOptions);
            console.log('Totals table initialized:', totalsGrid);
        } catch (error) {
            console.error('Error initializing totals table:', error);
        }
    } else {
        console.error('Totals table element not found');
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

    setTimeout(() => {
        console.log('Calling initial calculateTotals');
        calculateTotals();
    }, 1000);


});

