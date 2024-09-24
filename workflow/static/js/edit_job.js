document.addEventListener('DOMContentLoaded', function () {
    // Helper functions for currency formatting and total calculation
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

    // Grid options for Time, Materials, and Adjustments tables
    const gridOptions = {
        columnDefs: [
            { headerName: 'Description', field: 'description', editable: true },
            { headerName: 'Items', field: 'items', editable: true, valueParser: numberParser },
            { headerName: 'Mins/Item', field: 'minsPerItem', editable: true, valueParser: numberParser },
            {
                headerName: 'Total Minutes',
                field: 'totalMinutes',
                valueGetter: calculateTotalMinutes,
                editable: false,
                valueFormatter: currencyFormatter
            },
            { headerName: 'Rate', field: 'rate', editable: true, valueParser: numberParser, valueFormatter: currencyFormatter },
            {
                headerName: 'Total',
                field: 'total',
                valueGetter: calculateTotal,
                editable: false,
                valueFormatter: currencyFormatter
            },
        ],
        rowData: [{ description: '', items: 0, minsPerItem: 0, totalMinutes: 0, rate: 0, total: 0 }],
        defaultColDef: {
            sortable: true,
            resizable: true
        }
    };

    const materialsGridOptions = {
        columnDefs: [
            { headerName: 'Item Code', field: 'itemCode', editable: true },
            { headerName: 'Description', field: 'description', editable: true },
            { headerName: 'Markup %', field: 'markup', editable: true, valueParser: numberParser },
            { headerName: 'Quantity', field: 'quantity', editable: true, valueParser: numberParser },
            { headerName: 'Rate', field: 'rate', editable: true, valueParser: numberParser, valueFormatter: currencyFormatter },
            {
                headerName: 'Total',
                field: 'total',
                valueGetter: calculateTotal,
                editable: false,
                valueFormatter: currencyFormatter
            },
            { headerName: 'Comments', field: 'comments', editable: true },
        ],
        rowData: [{ itemCode: '', description: '', markup: 0, quantity: 0, rate: 0, total: 0, comments: '' }],
        defaultColDef: {
            sortable: true,
            resizable: true
        }
    };

    const adjustmentsGridOptions = {
        columnDefs: [
            { headerName: 'Description', field: 'description', editable: true },
            { headerName: 'Quantity', field: 'quantity', editable: true, valueParser: numberParser },
            { headerName: 'Amount', field: 'amount', editable: true, valueParser: numberParser, valueFormatter: currencyFormatter },
            {
                headerName: 'Total',
                field: 'total',
                valueGetter: calculateTotal,
                editable: false,
                valueFormatter: currencyFormatter
            },
            { headerName: 'Comments', field: 'comments', editable: true },
        ],
        rowData: [{ description: '', quantity: 0, amount: 0, total: 0, comments: '' }],
        defaultColDef: {
            sortable: true,
            resizable: true
        }
    };

    // Initialize AG Grid for each section: estimate, quote, reality
    const sections = ['estimate', 'quote', 'reality'];
    sections.forEach(section => {
        new agGrid.Grid(document.getElementById(`${section}TimeTable`), gridOptions);
        new agGrid.Grid(document.getElementById(`${section}MaterialsTable`), materialsGridOptions);
        new agGrid.Grid(document.getElementById(`${section}AdjustmentsTable`), adjustmentsGridOptions);
    });

    // Totals Table initialization
    const totalsGridOptions = {
        columnDefs: [
            { headerName: 'Category', field: 'category', editable: false },
            { headerName: 'Estimate', field: 'estimate', editable: false, valueFormatter: currencyFormatter },
            { headerName: 'Quote', field: 'quote', editable: false, valueFormatter: currencyFormatter },
            { headerName: 'Reality', field: 'reality', editable: false, valueFormatter: currencyFormatter },
        ],
        rowData: [
            { category: 'Total Labour', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Materials', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Adjustments', estimate: 0, quote: 0, reality: 0 },
            { category: 'Total Project Cost', estimate: 0, quote: 0, reality: 0 }
        ],
        defaultColDef: {
            sortable: true,
            resizable: true
        }
    };

    // Initialize Totals Table
    new agGrid.Grid(document.getElementById('totalsTable'), totalsGridOptions);

    // Recalculate project totals based on data in each section
    function calculateProjectTotals() {
        let totalLabour = 0, totalMaterials = 0, totalAdjustments = 0;

        // Calculate total for each table and section (estimate, quote, reality)
        sections.forEach(section => {
            const timeTable = agGrid.Grid.getInstance(document.getElementById(`${section}TimeTable`));
            const materialsTable = agGrid.Grid.getInstance(document.getElementById(`${section}MaterialsTable`));
            const adjustmentsTable = agGrid.Grid.getInstance(document.getElementById(`${section}AdjustmentsTable`));

            timeTable.forEachNode(node => totalLabour += node.data.total);
            materialsTable.forEachNode(node => totalMaterials += node.data.total);
            adjustmentsTable.forEachNode(node => totalAdjustments += node.data.total);
        });

        // Update totals in Totals Table
        const totalsTable = agGrid.Grid.getInstance(document.getElementById('totalsTable'));
        totalsTable.getRowNode(0).setDataValue('estimate', totalLabour);
        totalsTable.getRowNode(1).setDataValue('estimate', totalMaterials);
        totalsTable.getRowNode(2).setDataValue('estimate', totalAdjustments);
    }
});
