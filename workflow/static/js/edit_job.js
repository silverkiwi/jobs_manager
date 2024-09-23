document.addEventListener('DOMContentLoaded', function() {
    const noEntriesPlaceholder = "No entries";

    // Store references to Handsontable instances
    const handsontableInstances = {};

    function deleteIconRenderer(instance, td, row, col, prop, value, cellProperties) {
        const icon = document.createElement('span');
        icon.className = 'delete-icon';
        icon.innerHTML = '&#x1F5D1;'; // Unicode for trash bin
        icon.onclick = function() {
            instance.alter('remove_row', row);
        };
        td.innerHTML = ''; // Clear cell content
        td.appendChild(icon); // Add delete icon
        return td;
    }

    // Time Table settings
    const timeTableSettings = {
        colHeaders: ['Description', 'Items', 'Mins/Item', 'Total Minutes', 'Rate', 'Total'],
        data: [['', '', '', '', '', '']],
        columns: [
            {data: 0, type: 'text'}, // Description
            {data: 1, type: 'numeric'}, // Items
            {data: 2, type: 'numeric'}, // Mins/Item
            {data: 3, type: 'numeric', readOnly: true}, // Total Minutes (calculated elsewhere)
            {
                data: 4, // Rate column
                type: 'numeric',
                numericFormat: {
                    pattern: '$0,0.00', // Currency format
                    culture: 'en-US'
                }
            }, // Rate
            {
                data: 5, // Total column
                type: 'numeric',
                readOnly: true, // Read-only as it's calculated
                numericFormat: {
                    pattern: '$0,0.00', // Currency format
                    culture: 'en-US'
                }
            } // Total
        ],
        rowHeaders: false,
        contextMenu: true,
        minSpareRows: 1,
        afterChange: function (changes, source) {
            if (source === 'loadData') return;

            changes.forEach(function ([row, prop, oldVal, newVal]) {
                if (prop === 1 || prop === 4) { // If Items or Rate has changed
                    const items = this.getDataAtRowProp(row, 1); // Get Items
                    const rate = this.getDataAtRowProp(row, 4); // Get Rate
                    const total = (items * rate) || 0; // Calculate Total
                    this.setDataAtRowProp(row, 5, total.toFixed(2)); // Update Total column with $ formatting
                }
            }.bind(this)); // Bind 'this' to the Handsontable instance
            calculateProjectTotals();

        }
    };

    // Materials Table settings
    const materialsTableSettings = {
        colHeaders: ['Item Code', 'Description', 'Markup %', 'Quantity', 'Rate', 'Total', 'Comments'],
        data: [['', '', '', '', '', '', '']],
        columns: [
            {data: 0, type: 'text'}, // Item Code
            {data: 1, type: 'text'}, // Description
            {data: 2, type: 'numeric'}, // Markup %
            {data: 3, type: 'numeric'}, // Quantity
            {
                data: 4, // Rate column
                type: 'numeric',
                numericFormat: {
                    pattern: '$0,0.00', // Currency format
                    culture: 'en-US'
                }
            }, // Rate
            {
                data: 5, // Total column
                type: 'numeric',
                readOnly: true, // Read-only as it's calculated
                numericFormat: {
                    pattern: '$0,0.00', // Currency format
                    culture: 'en-US'
                }
            }, // Total
            {data: 6, type: 'text'} // Comments
        ],
        rowHeaders: false,
        contextMenu: true,
        minSpareRows: 1,
        afterChange: function (changes, source) {
            if (source === 'loadData') return;

            changes.forEach(function ([row, prop, oldVal, newVal]) {
                if (prop === 3 || prop === 4) { // If Quantity or Rate has changed
                    const quantity = this.getDataAtRowProp(row, 3); // Get Quantity
                    const rate = this.getDataAtRowProp(row, 4); // Get Rate
                    const total = (quantity * rate) || 0; // Calculate Total
                    this.setDataAtRowProp(row, 5, total.toFixed(2)); // Update Total column with $ formatting
                }
            }.bind(this)); // Bind 'this' to the Handsontable instance
            calculateProjectTotals();

        }
    };

    // Adjustments Table settings
    const adjustmentsTableSettings = {
        colHeaders: ['Description', 'Quantity', 'Amount', 'Total', 'Comments'],
        data: [['', '', '', '', '']],
        columns: [
            {data: 0, type: 'text'}, // Description
            {data: 1, type: 'numeric'}, // Quantity
            {
                data: 2, // Amount column
                type: 'numeric',
                numericFormat: {
                    pattern: '$0,0.00', // Currency format
                    culture: 'en-US'
                }
            }, // Amount
            {
                data: 3, // Total column
                type: 'numeric',
                readOnly: true, // Read-only as it's calculated
                numericFormat: {
                    pattern: '$0,0.00', // Currency format
                    culture: 'en-US'
                }
            }, // Total
            {data: 4, type: 'text'} // Comments
        ],
        rowHeaders: false,
        contextMenu: true,
        minSpareRows: 1,
        afterChange: function (changes, source) {
            if (source === 'loadData') return;

            changes.forEach(function ([row, prop, oldVal, newVal]) {
                // Update "Total Minutes" if "Items" or "Mins/Item" has changed
                if (prop === 1 || prop === 2) {  // Items or Mins/Item has changed
                    const items = this.getDataAtRowProp(row, 1);  // Get Items
                    const minsPerItem = this.getDataAtRowProp(row, 2);  // Get Mins/Item
                    const totalMinutes = (items * minsPerItem) || 0;  // Calculate Total Minutes
                    this.setDataAtRowProp(row, 3, totalMinutes.toFixed(2));  // Update Total Minutes column
                }

                // Update "Total" (Items * Rate)
                if (prop === 1 || prop === 4) {  // Items or Rate has changed
                    const items = this.getDataAtRowProp(row, 1);  // Get Items
                    const rate = this.getDataAtRowProp(row, 4);  // Get Rate
                    const total = (items * rate) || 0;  // Calculate Total
                    this.setDataAtRowProp(row, 5, total.toFixed(2));  // Update Total column with $ formatting
                }
            }.bind(this));  // Bind 'this' to the Handsontable instance
            calculateProjectTotals();
        }
    };

    timeTableSettings.licenseKey = 'non-commercial-and-evaluation';
    materialsTableSettings.licenseKey = 'non-commercial-and-evaluation';
    adjustmentsTableSettings.licenseKey = 'non-commercial-and-evaluation';

    // Initialize Time, Materials, and Adjustments tables for all sections dynamically
    function initializeTables(section) {
        handsontableInstances[`${section}TimeTable`] = new Handsontable(document.getElementById(`${section}TimeTable`), timeTableSettings);
        handsontableInstances[`${section}MaterialsTable`] = new Handsontable(document.getElementById(`${section}MaterialsTable`), materialsTableSettings);
        handsontableInstances[`${section}AdjustmentsTable`] = new Handsontable(document.getElementById(`${section}AdjustmentsTable`), adjustmentsTableSettings);
    }

    // Initialize tables for each section: estimate, quote, reality
    ['estimate', 'quote', 'reality'].forEach(section => initializeTables(section));

    // Totals Table initialization
    const totalsTableSettings = {
        data: [
            ['Total Labour', 0, 0, 0],
            ['Total Materials', 0, 0, 0],
            ['Total Adjustments', 0, 0, 0],
            ['Total Project Cost', 0, 0, 0]
        ],
        colHeaders: ['Category', 'Estimate', 'Quote', 'Reality'],
        columns: [
            {data: 0, type: 'text', readOnly: true},
            {data: 1, type: 'numeric', format: '$0,0.00', readOnly: true},  // Estimate
            {data: 2, type: 'numeric', format: '$0,0.00', readOnly: true},  // Quote
            {data: 3, type: 'numeric', format: '$0,0.00', readOnly: true}   // Reality
        ],
        rowHeaders: false,
        contextMenu: false
    };

    totalsTableSettings.licenseKey = 'non-commercial-and-evaluation';
    const totalsTable = new Handsontable(document.getElementById('totalsTable'), totalsTableSettings);

    // Calculate totals from the other tables and update the Totals Table
    function calculateProjectTotals() {
    // Totals for Estimates, Quotes, and Reality
        let estimateTotalLabour = 0, estimateTotalMaterials = 0, estimateTotalAdjustments = 0;
        let quoteTotalLabour = 0, quoteTotalMaterials = 0, quoteTotalAdjustments = 0;
        let realityTotalLabour = 0, realityTotalMaterials = 0, realityTotalAdjustments = 0;

        // Sum totals from Time tables (Labour)
        [['estimateTimeTable', estimateTotalLabour], ['quoteTimeTable', quoteTotalLabour], ['realityTimeTable', realityTotalLabour]].forEach(([id, labourTotal]) => {
            const table = handsontableInstances[id]; // Use stored instance
            table.getData().forEach(row => {
                labourTotal += row[5] || 0; // Add up 'Total' column
            });
        });

        // Sum totals from Materials tables
        [['estimateMaterialsTable', estimateTotalMaterials], ['quoteMaterialsTable', quoteTotalMaterials], ['realityMaterialsTable', realityTotalMaterials]].forEach(([id, materialsTotal]) => {
            const table = handsontableInstances[id]; // Use stored instance
            table.getData().forEach(row => {
                materialsTotal += (row[3] * row[4]) || 0; // Quantity * Rate
            });
        });

        // Sum totals from Adjustments tables
        [['estimateAdjustmentsTable', estimateTotalAdjustments], ['quoteAdjustmentsTable', quoteTotalAdjustments], ['realityAdjustmentsTable', realityTotalAdjustments]].forEach(([id, adjustmentsTotal]) => {
            const table = handsontableInstances[id]; // Use stored instance
            table.getData().forEach(row => {
                adjustmentsTotal += row[3] || 0; // Add up 'Total' column
            });
        });

        // Calculate total project cost for each column
        const estimateTotalProjectCost = estimateTotalLabour + estimateTotalMaterials + estimateTotalAdjustments;
        const quoteTotalProjectCost = quoteTotalLabour + quoteTotalMaterials + quoteTotalAdjustments;
        const realityTotalProjectCost = realityTotalLabour + realityTotalMaterials + realityTotalAdjustments;

        // Update totals table
        // Update Labour row
        totalsTable.setDataAtRowProp(0, 1, estimateTotalLabour); // Estimate Labour
        totalsTable.setDataAtRowProp(0, 2, quoteTotalLabour);    // Quote Labour
        totalsTable.setDataAtRowProp(0, 3, realityTotalLabour);  // Reality Labour

        // Update Materials row
        totalsTable.setDataAtRowProp(1, 1, estimateTotalMaterials); // Estimate Materials
        totalsTable.setDataAtRowProp(1, 2, quoteTotalMaterials);    // Quote Materials
        totalsTable.setDataAtRowProp(1, 3, realityTotalMaterials);  // Reality Materials

        // Update Adjustments row
        totalsTable.setDataAtRowProp(2, 1, estimateTotalAdjustments); // Estimate Adjustments
        totalsTable.setDataAtRowProp(2, 2, quoteTotalAdjustments);    // Quote Adjustments
        totalsTable.setDataAtRowProp(2, 3, realityTotalAdjustments);  // Reality Adjustments

        // Update Total Project Cost row
        totalsTable.setDataAtRowProp(3, 1, estimateTotalProjectCost); // Estimate Project Cost
        totalsTable.setDataAtRowProp(3, 2, quoteTotalProjectCost);    // Quote Project Cost
        totalsTable.setDataAtRowProp(3, 3, realityTotalProjectCost);  // Reality Project Cost
    }

});
