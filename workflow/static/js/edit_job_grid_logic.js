/*
 * File Overview:
 * ----------------
 * This file manages the creation and interaction of grids using AG Grid. It includes
 * functionality for dynamically initializing multiple grids (time, materials, adjustments)
 * across various sections (e.g., estimate, quote, reality), and includes a special revenue grid.
 * Later we might add cost with the revenue grid.
 *
 * Key Interactions:
 * - Autosave Integration:
 *   The autosave functionality depends on grid changes triggering an event that captures
 *   the data across all relevant grids. It is crucial that the APIs for each grid are correctly
 *   initialized and stored in `window.grids` to ensure autosave has access to the necessary data.
 *
 * - AG Grid API Storage:
 *   Each grid API is stored in `window.grids` once the grid is initialized. This is critical
 *   for autosave, `calculateTotalRevenue()`, and other inter-grid operations. The revenue grid is
 *   also included here, as it is required for proper calculation and data refresh.
 *
 * - AG Grid Version Compatibility:
 *   Ensure that changes align with AG Grid version 32.2.1. Be aware of deprecated properties
 *   and avoid using older APIs that may not be compatible with this version.
 *
 * Important Notes:
 * - The `onGridReady` function, inherited from `commonGridOptions`, is responsible for storing
 *   each grid's API in `window.grids`. Do not modify the initialization logic to exclude this step.
 * - Each grid API is crucial for the autosave mechanism. Breaking or missing the correct API
 *   initialization may lead to unexpected errors or the autosave failing silently.
 * - Maintain a consistent approach to API storage and avoid changes that bypass or duplicate
 *   API handling in `onGridReady`.
 */

import { createNewRow, getGridData } from '/static/js/deseralise_job_pricing.js';
import { handlePrintJob, handleExportCosts, debouncedAutosave, copyEstimateToQuote, collectAllData } from './edit_job_form_autosave.js';
import { renderMessages } from './timesheet/timesheet_entry/messages.js';

// console.log('Grid logic script is running');

// This listener is for the entries towards the top.  The material and description fields, etc.
document.addEventListener('DOMContentLoaded', () => {
    const materialField = document.getElementById('material_gauge_quantity');
    const descriptionField = document.getElementById('job_description');

    if (!materialField || !descriptionField) {
        throw new Error('Required fields material_gauge_quantity and/or job_description are missing from page');
    }

    const autoExpand = field => {
        field.style.height = 'inherit';
        const computed = window.getComputedStyle(field);
        const height = ['border-top-width', 'padding-top', 'padding-bottom', 'border-bottom-width']
            .reduce((sum, prop) => sum + parseInt(computed.getPropertyValue(prop), 10), field.scrollHeight);
        field.style.height = `${height}px`;
    };

    [materialField, descriptionField].forEach(field => {
        field.addEventListener('input', () => autoExpand(field));
        autoExpand(field);
    });
});

// This listener is for the job pricing grid
document.addEventListener('DOMContentLoaded', function () {
    function currencyFormatter(params) {
        if (params.value === undefined) {
            // console.error('currencyFormatter error: value is undefined for the following params:', params);
            return '$0.00';  // Return a fallback value so the grid doesn't break
        }
        return '$' + params.value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function numberParser(params) {
        return Number(params.newValue);
    }

    function calculateGridHeight(gridApi, numRows) {
        const rowHeight = gridApi.getSizesForCurrentTheme().rowHeight || 28;
        const headerElement = document.querySelector('.ag-header');
        const headerHeight = headerElement ? headerElement.offsetHeight : 32;

        return numRows * rowHeight + headerHeight;
    }

    function deleteIconCellRenderer(params) {
        const isLastRow = params.api.getDisplayedRowCount() === 1;
        const iconClass = isLastRow ? 'delete-icon disabled' : 'delete-icon';
        return `<span class='${iconClass}'>🗑️</span>`;
    }

    function onDeleteIconClicked(params) {
        if (params.api.getDisplayedRowCount() > 1) {
            params.api.applyTransaction({ remove: [params.node.data] });
            calculateTotalRevenue(); // Recalculate totals after row deletion
        }
    }


    function onCellKeyDown(params) {
        if (params.event.key === 'Enter') {
            const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
            if (isLastRow) {
                const newRow = createNewRow(params.context.gridType);
                if (newRow) {
                    params.api.applyTransaction({ add: [newRow] });
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
        return [createNewRow(gridType) || {}];  // Return the result of createNewRow as an array
    }

    function calculateTotalRevenue() {
        const revenueTotals = {
            time: { estimate: 0, quote: 0, reality: 0 },
            materials: { estimate: 0, quote: 0, reality: 0 },
            adjustments: { estimate: 0, quote: 0, reality: 0 }
        };

        const sections = ['estimate', 'quote', 'reality'];
        const gridTypes = ['Time', 'Materials', 'Adjustments'];

        sections.forEach(section => {
            gridTypes.forEach(gridType => {
                const gridKey = `${section}${gridType}Table`;
                const gridData = window.grids[gridKey];
                if (gridData && gridData.api) {
                    gridData.api.forEachNode(node => {
                        const rowCost = parseFloat(node.data.cost) || 0;
                        const rowRevenue = parseFloat(node.data.revenue) || 0;
                        const revenueType = gridType.toLowerCase();
                        revenueTotals[revenueType][section] += rowRevenue;
                    });
                }
            });
        });

        const revenueGrid = window.grids['revenueTable'];
        if (revenueGrid && revenueGrid.api) {
            revenueGrid.api.forEachNode((node, index) => {
                const data = node.data;
                switch (index) {
                    case 0: // Total Time
                        data.estimate = revenueTotals.time.estimate;
                        data.quote = revenueTotals.time.quote;
                        data.reality = revenueTotals.time.reality;
                        break;
                    case 1: // Total Materials
                        data.estimate = revenueTotals.materials.estimate;
                        data.quote = revenueTotals.materials.quote;
                        data.reality = revenueTotals.materials.reality;
                        break;
                    case 2: // Total Adjustments
                        data.estimate = revenueTotals.adjustments.estimate;
                        data.quote = revenueTotals.adjustments.quote;
                        data.reality = revenueTotals.adjustments.reality;
                        break;
                    case 3: // Total Project Cost
                        data.estimate = revenueTotals.time.estimate + revenueTotals.materials.estimate + revenueTotals.adjustments.estimate;
                        data.quote = revenueTotals.time.quote + revenueTotals.materials.quote + revenueTotals.adjustments.quote;
                        data.reality = revenueTotals.time.reality + revenueTotals.materials.reality + revenueTotals.adjustments.reality;
                        break;
                }
            })
        }

        revenueGrid.api.refreshCells();
    }


    function calculateTotalCost() {
        const totals = {
            time: { estimate: 0, quote: 0, reality: 0 },
            materials: { estimate: 0, quote: 0, reality: 0 },
            adjustments: { estimate: 0, quote: 0, reality: 0 }
        };

        const sections = ['estimate', 'quote', 'reality'];
        const gridTypes = ['Time', 'Materials', 'Adjustments'];

        sections.forEach(section => {
            gridTypes.forEach(gridType => {
                const gridKey = `${section}${gridType}Table`;
                const gridData = window.grids[gridKey];
                if (gridData && gridData.api) {
                    gridData.api.forEachNode(node => {
                        let rowCost = 0;

                        // Different cost calculation for each type
                        if (gridType === 'Time') {
                            // Cost = (minutes * wage_rate) / 60
                            const minutes = parseFloat(node.data.total_minutes) || 0;
                            const wageRate = parseFloat(node.data.wage_rate) || 0;
                            rowCost = (minutes * wageRate) / 60;
                        } else if (gridType === 'Materials') {
                            // Cost = quantity * unit_cost
                            const quantity = parseFloat(node.data.quantity) || 0;
                            const unitCost = parseFloat(node.data.unit_cost) || 0;
                            rowCost = quantity * unitCost;
                        } else if (gridType === 'Adjustments') {
                            // Cost = cost_adjustment
                            rowCost = parseFloat(node.data.cost_adjustment) || 0;
                        }

                        const costType = gridType.toLowerCase();
                        totals[costType][section] += rowCost;
                    });
                }
            });
        });

        const costGrid = window.grids['costsTable'];
        if (costGrid && costGrid.api) {
            costGrid.api.forEachNode((node, index) => {
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
            });
            costGrid.api.refreshCells();
        }
    }

    function fetchMaterialsMarkup(rowData) {
        if (rowData.materialsMarkup !== undefined) {
            return Promise.resolve(rowData.materialsMarkup);
        }

        return fetch('/api/company_defaults')
            .then(response => response.json())
            .then(companyDefaults => {
                rowData.materialsMarkup = parseFloat(companyDefaults.materials_markup) || 0.2;
                return rowData.materialsMarkup;
            })
            .catch(error => {
                console.error('Error fetching company defaults:', error);
                return 0.2;
            });
    }

    function calculateRetailRate(costRate, markupRate) {
        return costRate + (costRate * markupRate);
    }

    function getRetailRate(params) {
        if (params.data.unit_revenue !== undefined) {
            return params.data.unit_revenue; // Return stored value
        }

        // Fetch markup asynchronously, but return the last known value immediately
        fetchMaterialsMarkup(params.data).then(markupRate => {
            if (!params.data.isManualOverride) {
                params.data.unit_revenue = calculateRetailRate(params.data.unit_cost, markupRate);
                params.api.refreshCells({ rowNodes: [params.node], columns: ['unit_revenue'], force: true });
            }
        });

        return params.data.unit_revenue || 0; // Default fallback value
    }

    function setRetailRate(params) {
        let newValue = parseFloat(params.newValue);
        let costRate = parseFloat(params.data.unit_cost) || 0;

        fetchMaterialsMarkup(params.data).then(markupRate => {
            if (!isNaN(newValue) && newValue !== calculateRetailRate(costRate, markupRate)) {
                params.data.isManualOverride = true;
            }

            if (!params.data.isManualOverride) {
                params.data.unit_revenue = calculateRetailRate(costRate, markupRate);
            } else {
                params.data.unit_revenue = newValue;
            }

            params.api.refreshCells({ rowNodes: [params.node], columns: ['unit_revenue'], force: true });
        });

        return true;
    }

    const commonGridOptions = {
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
            //            console.log(`Grid Key: ${gridKey}, Initial Grid Height: ${initialGridHeight}`);
            gridElement.style.height = `${initialGridHeight}px`;

            window.grids[gridKey] = { api: params.api };
            // console.log(`Grid ${gridKey} initialized with API:`, window.grids[gridKey]);

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
                data.total_minutes = (data.items || 0) * (data.mins_per_item || 0);
                data.revenue = (data.total_minutes || 0) * (data.charge_out_rate / 60.0 || 0);

                const hours = (data.total_minutes / 60).toFixed(1);
                data.total_minutes_display = `${data.total_minutes} (${hours} hours)`;

            } else if (gridType === 'MaterialsTable') {
                if (event.column.colId === 'unit_cost') {
                    if (!data.isManualOverride) {
                        fetchMaterialsMarkup(data).then(markupRate => {
                            data.unit_revenue = calculateRetailRate(data.unit_cost, markupRate);
                            event.api.refreshCells({ rowNodes: [event.node], columns: ['unit_revenue'], force: true });
                        });
                    }
                }

                if (event.column.colId === 'unit_revenue') {
                    // Mark as manually overridden only if user types in this cell
                    if (event.newValue !== null && event.newValue !== undefined) {
                        data.isManualOverride = true;
                    }
                }

                data.revenue = (data.quantity || 0) * (data.unit_revenue || 0);
            }

            event.api.refreshCells({ rowNodes: [event.node], columns: ['revenue', 'total_minutes'], force: true });

            debouncedAutosave(event);
            calculateTotalRevenue();
            calculateTotalCost();

        }
    };

    const trashCanColumn = {
        headerName: '',
        field: '',
        width: 40,
        cellRenderer: deleteIconCellRenderer,
        onCellClicked: onDeleteIconClicked,
        cellStyle: {
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            padding: 0
        }
    };

    const timeGridOptions = {
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
                minWidth: 110,
                flex: 1
            },

            // Made the following hidden and non-editable, as requested in this card: https://trello.com/c/G6gaunS1
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


    const materialsGridOptions = {
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

    const adjustmentsGridOptions = {
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

    const sections = ['estimate', 'quote', 'reality'];
    const workType = ['Time', 'Materials', 'Adjustments'];
    window.grids = {};

    sections.forEach(section => {
        workType.forEach(work => {
            const gridType = `${work}Table`;  // Assigning the grid type dynamically based on the work type
            const gridKey = `${section}${gridType}`;  // Create the full key for identifying the grid
            const gridElement = document.querySelector(`#${gridKey}`);

            let specificGridOptions;
            switch (gridType) {
                case 'TimeTable':
                    if (section === 'reality') {
                        specificGridOptions = JSON.parse(JSON.stringify(timeGridOptions));
                        specificGridOptions.columnDefs.forEach(col => {
                            // Make all columns non-editable for reality section
                            col.editable = false;
                            // Preserve link column renderer but keep it non-editable
                            if (col.field === 'link') {
                                col.cellRenderer = timeGridOptions.columnDefs.find(c => c.field === 'link').cellRenderer;
                            }
                        });
                        break;
                    }
                    specificGridOptions = JSON.parse(JSON.stringify(timeGridOptions));
                    // Hide link column for estimate and quote sections
                    specificGridOptions.columnDefs = specificGridOptions.columnDefs.map(col => {
                        if (col.field === 'link') {
                            return { ...col, hide: true };
                        }
                        return col;
                    });
                    break;
                case 'MaterialsTable':
                    specificGridOptions = materialsGridOptions;
                    break;
                case 'AdjustmentsTable':
                    specificGridOptions = adjustmentsGridOptions;
                    break;
            }

            if (!latest_job_pricings_json) {
                throw new Error('latest_job_pricings_json must be loaded before grid initialization');
            }

            const sectionData = latest_job_pricings_json[`${section}_pricing`];
            if (!sectionData) {
                console.warn(`Data not found for section '${section}'. Assuming this is a new job.`);
            }

            let rowData = getGridData(section, gridType);
            if (rowData.length === 0) {
                rowData = [createNewRow(gridType)];
            }

            const gridOptions = {
                ...commonGridOptions,
                ...specificGridOptions,
                context: { section, gridType: `${gridType}`, gridKey: gridKey },
                rowData: rowData  // Set initial row data in gridOptions
            };

            const gridInstance = agGrid.createGrid(gridElement, gridOptions);

            // Set row data after initializing the grid
            gridInstance.setGridOption('rowData', rowData);
        });
    });

    // Grid options for Totals table (default 4 rows, autoHeight for proper resizing)
    const revenueGridOptions = {
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

    const costGridOptions = {
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


    const revenueTableEl = document.querySelector('#revenueTable');
    if (revenueTableEl) {
        try {
            agGrid.createGrid(revenueTableEl, revenueGridOptions);
            // console.log('Revenue table initialized:', revenueGrid);
        } catch (error) {
            console.error('Error initializing revenue table:', error);
        }
    } else {
        console.error('Revenue table element not found');
    }

    const costsTableEl = document.querySelector('#costsTable');
    if (costsTableEl) {
        try {
            agGrid.createGrid(costsTableEl, costGridOptions);
            // console.log('Revenue table initialized:', revenueGrid);
        } catch (error) {
            console.error('Error initializing costs table:', error);
        }
    } else {
        console.error('Costs table element not found');
    }


    setTimeout(() => {
        const expectedGridCount = sections.length * workType.length + 2; // 3 secionds of 3 grids, plus revenue and costs totals
        const actualGridCount = Object.keys(window.grids).length;

        if (actualGridCount !== expectedGridCount) {
            console.error(`Not all grids were initialized. Expected: ${expectedGridCount}, Actual: ${actualGridCount}`);
        } else {
            console.log('All grids successfully initialized.');
        }
    }, 3000); // 3-second delay to allow all grids to finish initializing


    setTimeout(() => {
        calculateTotalRevenue();
    }, 1000);

    document.body.addEventListener('click', function (event) {
        const buttonId = event.target.id;
        const jobId = getJobIdFromUrl();

        switch (buttonId) {
            case 'copyEstimateToQuote':
                copyEstimateToQuote();
                calculateTotalCost();
                calculateTotalRevenue();
                break;

            case 'quoteJobButton':
                createXeroDocument(jobId, 'quote');
                break;

            case 'deleteQuoteButton':
                deleteXeroDocument(jobId, 'quote');
                break;

            case 'invoiceJobButton':
                createXeroDocument(jobId, 'invoice');
                break;

            case 'deleteInvoiceButton':
                deleteXeroDocument(jobId, 'invoice');
                break;

            case 'printJobButton':
                handlePrintJob();
                break;

            case 'acceptQuoteButton':
                const currentDateTimeISO = new Date().toISOString();
                document.getElementById('quote_acceptance_date_iso').value = currentDateTimeISO;
                console.log(`Quote acceptance date set to: ${currentDateTimeISO}`);
                debouncedAutosave();
                break;

            case 'contactClientButton':
                showQuoteModal(jobId, 'gmail', true);
                break;

            case 'saveEventButton':
                handleSaveEventButtonClick(jobId);
                break;

            default:
                // Random clicks not on buttons don't count - don't even log them
                break;
        }
    });
});

function getJobIdFromUrl() {
    return window.location.pathname.split('/')[2];
}

function showQuoteModal(jobId, provider = 'gmail', contactOnly = false) {
    if (contactOnly) {
        sendQuoteEmail(jobId, provider, true)
            .catch(error => {
                console.error('Error sending quote email:', error);
                renderMessages([{ level: 'error', message: 'Failed to send quote email.' }]);
            });
        return;
    }

    const modalHtml = `
        <div class='modal fade' id='quoteModal' tabindex='-1' role='dialog' aria-labelledby='quoteModalLabel' aria-hidden='true'>
            <div class='modal-dialog' role='document'>
                <div class='modal-content'>
                    <div class='modal-header'>
                        <h5 class='modal-title' id='quoteModalLabel'>Preview and Send Quote</h5>
                        <button type='button' class='btn-close' data-bs-dismiss='modal' aria-label='Close'></button>
                    </div>
                    <div class='modal-body'>
                        <p>The quote has been generated. Please preview it in the opened tab and confirm if you'd like to send it to the client.</p>
                        
                        <div class='alert alert-info' role='alert'>
                            <p class='mb-1'>If the quote looks correct, please download the PDF from the opened tab and click 'Send Quote'.</p>
                            <hr>
                            <p class='mb-1'>This will open your email client where you can compose your message and attach the downloaded PDF</p>
                            <hr>
                            <p class='mb-0'><b>Please ensure the PDF is properly attached before sending the email to the client.</b></p>
                        </div>

                        <div id='email-alert-container' class='alert-container'></div>
                    </div>
                    <div class='modal-footer'>
                        <button type='button' class='btn btn-secondary' data-bs-dismiss='modal'>Close</button>
                        <button id='sendQuoteEmailButton' type='button' class='btn btn-primary'>Send Quote</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const quoteModal = new bootstrap.Modal(document.getElementById('quoteModal'));
    quoteModal.show();

    const sendQuoteButton = document.getElementById('sendQuoteEmailButton');

    // Remove duplicated event listeners
    sendQuoteButton.replaceWith(sendQuoteButton.cloneNode(true));

    document.getElementById('sendQuoteEmailButton').addEventListener('click', async () => {
        try {
            const data = await sendQuoteEmail(jobId, provider);
            if (data.success) {
                renderMessages([{ level: 'success', message: 'Email client opened successfully.' }], 'email-alert-container');
            } else {
                renderMessages([{ level: 'error', message: 'Failed to open email client.' }], 'email-alert-container');
            }
        } catch (error) {
            renderMessages([{ level: 'error', message: `Error: ${error.message}` }], 'email-alert-container');
        }
    });
}

async function sendQuoteEmail(jobId, provider = 'gmail', contactOnly = false) {
    try {
        const endpoint = `/api/quote/${jobId}/send-email/?contact_only=${contactOnly}`;
        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();

        if (data.success && data.mailto_url) {
            const email = data.mailto_url.match(/mailto:([^?]+)/)?.[1];
            const subject = encodeURIComponent(data.mailto_url.match(/subject=([^&]+)/)?.[1]);
            const body = encodeURIComponent(data.mailto_url.match(/body=([^&]+)/)?.[1]);

            let emailUrl = '';

            if (provider === 'gmail') {
                emailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${email}&su=${subject}&body=${body}`;
            } else if (provider === 'outlook') {
                emailUrl = `https://outlook.office.com/mail/deeplink/compose?to=${email}&subject=${subject}&body=${body}`;
            } else {
                throw new Error('Unsupported email provider.');
            }

            window.open(emailUrl, '_blank');
        } else if (!data.success) {
            console.error('Error sending email:', data.error);
        }

        return data;
    } catch (error) {
        renderMessages([{ level: 'error', message: `Error sending email: ${error.message}` }], 'email-alert-container');
        console.error('Error sending email:', error);
        throw error;
    }
}

// Function to format the event type (e.g., 'manual_note' -> 'Manual Note')
function formatEventType(eventType) {
    return eventType
        .replaceAll('_', ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
    }).format(date);
}

function addEventToTimeline(event, jobEventsList) {
    const eventType = formatEventType(event.event_type);

    const newEventHtml = `
        <div class='timeline-item list-group-item'>
            <div class='d-flex w-100 justify-content-between'>
                <div class='timeline-date text-muted small'>${formatTimestamp(event.timestamp)}</div>
            </div>
            <div class='timeline-content'>
                <h6 class='mb-1'>${eventType}</h6>
                <p class='mb-1'>${event.description}</p>
                <small class='text-muted'>By ${event.staff}</small>
            </div>
        </div>
    `;
    jobEventsList.insertAdjacentHTML('afterbegin', newEventHtml);
}

function handleSaveEventButtonClick(jobId) {
    const eventDescriptionField = document.getElementById('eventDescription');
    const description = eventDescriptionField.value.trim();

    if (!description) {
        renderError('Please enter an event description.');
        return;
    }

    const jobEventsList = document.querySelector('.timeline.list-group');
    const noEventsMessage = jobEventsList.querySelector('.text-center.text-muted');

    fetch(`/api/job-event/${jobId}/add-event/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
        body: JSON.stringify({ description }),
    })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                renderError(data.error || 'Failed to add an event.');
                return;
            }

            if (noEventsMessage) {
                noEventsMessage.remove();
            }

            addEventToTimeline(data.event, jobEventsList);

            // Clear the input field and hide the modal
            eventDescriptionField.value = '';
            const modal = bootstrap.Modal.getInstance(document.getElementById('addJobEventModal'));
            modal.hide();
        })
        .catch(error => {
            console.error('Error adding job event:', error);
            renderError('Failed to add job event. Please try again.');
        });
}

function createXeroDocument(jobId, type) {
    console.log(`Creating Xero ${type} for job ID: ${jobId}`);

    if (!jobId) {
        console.error('Job ID is missing');
        renderMessages([{ level: 'error', message: `Job id is missing!` }]);
        return;
    }

    const endpoint = type === 'invoice'
        ? `/api/xero/create_invoice/${jobId}`
        : `/api/xero/create_quote/${jobId}`;

    console.log(`Making POST request to endpoint: ${endpoint}`);

    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
    })
        .then((response) => {
            console.log(`Received response with status: ${response.status}`);
            if (!response.ok) {
                return response.json().then((data) => {
                    console.log('Response not OK, checking for redirect:', data);
                    if (data.redirect_to_auth) {
                        console.log('Auth redirect required, preparing redirect message');
                        renderMessages(
                            [
                                {
                                    level: 'error',
                                    message: 'Your Xero session seems to have ended. Redirecting you to the Xero login in seconds.'
                                }
                            ]
                        );

                        const sectionId = type === 'invoice' ? 'workflow-section' : 'quoteTimeTable';
                        setTimeout(() => {
                            const redirectUrl = `/api/xero/authenticate/?next=${encodeURIComponent(
                                `${window.location.pathname}#${sectionId}`
                            )}`;
                            console.log(`Redirecting to: ${redirectUrl}`);
                            window.location.href = redirectUrl;
                        }, 3000);

                        return;
                    }
                    throw new Error(data.message || 'Failed to create document.');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Processing response data:', data);

            if (!data) {
                console.error('No data received from server');
                renderMessages([{ level: 'error', message: 'Your Xero session seems to have ended. Redirecting you to the Xero login in seconds.' }]);
                return;
            }

            if (!data.success) {
                console.error('Document creation failed:', data.messages);
                renderMessages(data.messages || [{ level: 'error', message: 'Failed to delete document.' }]);
                return;
            }

            console.log(`${type} created successfully with Xero ID: ${data.xero_id}`);

            const documentSummary = `
            <div class='card'>
                <div class='card-header bg-success text-white'>
                    ${type === 'invoice' ? 'Invoice' : 'Quote'} Created Successfully
                </div>
                <div class='card-body'>
                    <p><strong>Xero ID:</strong> ${data.xero_id}</p>
                    <p><strong>Client:</strong> ${data.client}</p>
                    ${data.invoice_url ? `<a href='${data.invoice_url}' target='_blank' class='btn btn-info'>Go to Xero</a>` : ''}
                    ${data.quote_url ? `<a href='${data.quote_url}' target='_blank' class='btn btn-info'>Go to Xero</a>` : ''}
                    <div class="alert alert-info mt-3">
                        <small>If the button above doesn't work, you can search for the Xero ID <strong>${data.xero_id}</strong> directly in Xero to find this document.</small>
                    </div>
                </div>
            </div>
            `;

            console.log('Updating document buttons and UI');
            handleDocumentButtons(type, data.invoice_url || data.quote_url, "POST");

            document.getElementById('alert-modal-body').innerHTML = documentSummary;
            new bootstrap.Modal(document.getElementById('alert-container')).show();
        })
        .catch(error => {
            console.error('Error creating Xero document:', error);
            renderMessages([{ level: 'error', message: `An error occurred: ${error.message}` }]);
        });
}

function handleDocumentButtons(type, online_url, method) {
    console.log(`Handling document buttons for type: ${type}, method: ${method}`);

    const documentButton = document.getElementById(type === 'invoice' ? 'invoiceJobButton' : 'quoteJobButton');
    console.log(`Document button found: ${documentButton ? 'yes' : 'no'}`);

    const statusCheckbox = document.getElementById(type === 'invoice' ? 'invoiced_checkbox' : 'quoted_checkbox');
    console.log(`Status checkbox found: ${statusCheckbox ? 'yes' : 'no'}`);

    const deleteButton = document.getElementById(type === 'invoice' ? 'deleteInvoiceButton' : 'deleteQuoteButton')
    console.log(`Delete button found: ${deleteButton ? 'yes' : 'no'}`);

    const xeroLink = document.getElementById(type === 'invoice' ? 'invoiceUrl' : 'quoteUrl');
    console.log(`Xero link found: ${xeroLink ? 'yes' : 'no'}`);

    if (online_url) {
        console.log(`Setting Xero link href to: ${online_url}`);
        xeroLink.href = online_url;
    }

    switch (method) {
        case 'POST':
            console.log('Handling POST method');
            documentButton.disabled = true;
            deleteButton.style.display = 'inline-block';

            statusCheckbox.disabled = false;
            statusCheckbox.checked = true;

            xeroLink.style.display = 'inline-block';
            break;

        case 'DELETE':
            console.log('Handling DELETE method');
            documentButton.disabled = false;
            deleteButton.style.display = 'none';

            statusCheckbox.disabled = true;
            statusCheckbox.checked = false;

            xeroLink.style.display = 'none';
    }
    console.log('Document button handling complete');
}

function deleteXeroDocument(jobId, type) {
    console.log(`Deleting Xero ${type} for job ID: ${jobId}`);

    if (!confirm(`Are you sure you want to delete this ${type}?`)) {
        console.log('User cancelled delete operation');
        return;
    }

    const endpoint = type === 'invoice'
        ? `/api/xero/delete_invoice/${jobId}`
        : `/api/xero/delete_quote/${jobId}`;

    console.log(`Making DELETE request to endpoint: ${endpoint}`);

    fetch(endpoint, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
    })
        .then((response) => {
            console.log(`Received response with status: ${response.status}`);
            if (!response.ok) {
                return response.json().then((data) => {
                    console.log('Response not OK, checking for redirect:', data);
                    if (data.redirect_to_auth) {
                        console.log('Auth redirect required, preparing redirect message');
                        const sectionId = type === 'invoice' ? 'workflow-section' : 'quoteTimeTable';
                        setTimeout(() => {
                            const redirectUrl = `/api/xero/authenticate/?next=${encodeURIComponent(
                                `${window.location.pathname}#${sectionId}`
                            )}`;
                            console.log(`Redirecting to: ${redirectUrl}`);
                            window.location.href = redirectUrl;
                        }, 3000);

                        return;
                    }
                    throw new Error(data.message || 'Failed to delete document.');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Processing response data:', data);

            if (!data) {
                console.error('No data received from server');
                renderMessages([{ level: 'error', message: 'Your Xero session seems to have ended. Redirecting you to the Xero login in seconds.' }]);
                return;
            }

            if (!data.success) {
                renderMessages(data.messages);
                return;
            }

            console.log('Document deleted successfully, updating UI');
            handleDocumentButtons(type, null, 'DELETE');
            renderMessages(data.messages);
        })
        .catch(error => {
            console.error('Error deleting Xero document:', error);
            renderMessages([{ level: 'error', message: `An error occurred: ${error.message}` }]);
        });
}
