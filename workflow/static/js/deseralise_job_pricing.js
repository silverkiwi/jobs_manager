// Deserialize entryFormsData
document.addEventListener('DOMContentLoaded', function () {
    const entryFormsElement = document.getElementById('entryFormsData');
    if (entryFormsElement) {
        try {
            console.log('Debug: Raw entryFormsData content:', entryFormsElement.textContent);
            window.entry_forms = JSON.parse(entryFormsElement.textContent);
            console.log('Debug: Loaded entry_forms data:', window.entry_forms);
        } catch (error) {
            console.error('Failed to parse entry forms data:', error);
        }
    } else {
        console.error('Could not find entry forms data.');
    }
});

function getGridData(section, gridType) {
    // Check if entry_forms data is available globally
    if (!window.entry_forms) {
        console.error('Error: entry_forms data is not loaded.');
        return [createNewRow(gridType)];
    }

    // Validate if the requested section exists in entry_forms
    const sectionData = window.entry_forms[section];
    if (!sectionData || !sectionData[gridType]) {
        console.log(`Debug: No data found for section "${section}" and grid type "${gridType}". Creating a new row.`);
        return [createNewRow(gridType)];
    }

    // Return the existing entries for the section and gridType
    return loadExistingJobEntries(sectionData[gridType], gridType);
}

function loadExistingJobEntries(entries, gridType) {
    switch (gridType) {
        case 'time':
            return loadExistingJobTimeEntries(entries);
        case 'material':
            return loadExistingJobMaterialEntries(entries);
        case 'adjustment':
            return loadExistingJobAdjustmentEntries(entries);
        default:
            console.error(`Unknown grid type: "${gridType}"`);
            return [createNewRow(gridType)];
    }
}

function loadExistingJobTimeEntries(entries) {
    console.log(`Debug: Found ${entries.length} time entries.`);
    return entries.map(entry => ({
        description: entry.description,
        items: entry.items,
        mins_per_item: entry.mins_per_item,
        wage_rate: entry.wage_rate,
        charge_out_rate: entry.charge_out_rate,
        total_minutes: entry.total_minutes,
        total: entry.total,
    }));
}

function loadExistingJobMaterialEntries(entries) {
    console.log(`Debug: Found ${entries.length} material entries.`);
    return entries.map(entry => ({
        item_code: entry.item_code,
        description: entry.description,
        quantity: entry.quantity,
        cost_price: entry.cost_price,
        retail_price: entry.retail_price,
        total: entry.total,
        comments: entry.comments,
    }));
}

function loadExistingJobAdjustmentEntries(entries) {
    console.log(`Debug: Found ${entries.length} adjustment entries.`);
    return entries.map(entry => ({
        description: entry.description,
        cost_adjustment: entry.cost_adjustment,
        price_adjustment: entry.price_adjustment,
        comments: entry.comments,
        total: entry.total,
    }));
}

function createNewRow(gridType) {
    const companyDefaults = document.getElementById('companyDefaults');
    const defaultWageRate = parseFloat(companyDefaults.dataset.wageRate);
    const defaultChargeOutRate = parseFloat(companyDefaults.dataset.chargeOutRate);

    switch (gridType) {
        case 'time':
            return { description: '', items: 0, mins_per_item: 0, wage_rate: defaultWageRate, charge_out_rate: defaultChargeOutRate, total_minutes: 0, total: 0 };
        case 'material':
            return { item_code: '', description: '', quantity: 0, cost_price: 0, retail_price: 0, total: 0, comments: '' };
        case 'adjustment':
            return { description: '', cost_adjustment: 0, price_adjustment: 0, comments: '', total: 0 };
        default:
            console.error(`Unknown grid type for new row creation: "${gridType}"`);
            return {};
    }
}


