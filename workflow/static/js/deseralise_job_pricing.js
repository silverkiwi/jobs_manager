// Deserialize entryFormsData
document.addEventListener('DOMContentLoaded', function () {
  // Update the HTML element ID to match the backend context
  const latestJobPricingsElement = document.getElementById(
    'latestJobPricingsData'
  );
  if (latestJobPricingsElement) {
    try {
      // Log raw content to debug
      console.log(
        'Debug: Raw latestJobPricingsData content:',
        latestJobPricingsElement.textContent
      );
      // Use snake case for consistency with backend variable names
      window.latest_job_pricings_json = JSON.parse(
        latestJobPricingsElement.textContent
      );
      console.log(
        'Debug: Loaded latest job pricing data:',
        window.latest_job_pricings_json
      );
    } catch (error) {
      console.error('Failed to parse latest job pricing data:', error);
    }
  } else {
    console.error('Could not find latest job pricing data.');
  }
});

document.addEventListener('DOMContentLoaded', function () {
  // Update the HTML element ID to match the backend context
  const historicalJobPricingsElement = document.getElementById(
    'historicalJobPricingsData'
  );
  if (historicalJobPricingsElement) {
    try {
      // Log raw content to debug
      console.log(
        'Debug: Raw historicalJobPricingsElement content:',
        historicalJobPricingsElement.textContent
      );
      // Use snake case for consistency with backend variable names
      window.historical_job_pricings_json = JSON.parse(
        historicalJobPricingsElement.textContent
      );
      console.log(
        'Debug: Loaded historical job pricing data:',
        window.historical_job_pricings_json
      );
    } catch (error) {
      console.error('Failed to parse Historical job pricing data:', error);
    }
  } else {
    console.error('Could not find historical job pricing data.');
  }
});

function getGridData(section, gridType) {
  // Check if latest_job_pricings_json data is available globally
  if (!window.latest_job_pricings_json) {
    console.error('Error: latest_job_pricings_json data is not loaded.');
    return [createNewRow(gridType)];
  }

  // Update to use the correct field names (_pricing suffix)
  const sectionKey = `${section}_pricing`;

  // Validate if the requested section exists in latest_job_pricings_json
  const sectionData = window.latest_job_pricings_json[sectionKey];
  if (!sectionData || !sectionData[gridType]) {
    console.log(
      `Debug: No data found for section "${sectionKey}" and grid type "${gridType}". Creating a new row.`
    );
    return [createNewRow(gridType)];
  }

  // Return the existing entries for the section and gridType
  return loadExistingJobEntries(sectionData[gridType], gridType);
}

function loadExistingJobEntries(entries, gridType) {
  switch (gridType) {
    case 'TimeTable':
      return loadExistingJobTimeEntries(entries);
    case 'MaterialsTable':
      return loadExistingJobMaterialEntries(entries);
    case 'AdjustmentsTable':
      return loadExistingJobAdjustmentEntries(entries);
    default:
      console.error(`Unknown grid type: "${gridType}"`);
      return [createNewRow(gridType)];
  }
}

function loadExistingJobTimeEntries(entries) {
  console.log(`Debug: Found ${entries.length} time entries.`);
  return entries.map((entry) => ({
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
  return entries.map((entry) => ({
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
  return entries.map((entry) => ({
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
  const defaultChargeOutRate = parseFloat(
    companyDefaults.dataset.chargeOutRate
  );

  switch (gridType) {
    case 'TimeTable':
      return {
        description: '',
        items: 0,
        mins_per_item: 0,
        wage_rate: defaultWageRate,
        charge_out_rate: defaultChargeOutRate,
        total_minutes: 0,
        total: 0,
      };
    case 'MaterialsTable':
      return {
        item_code: '',
        description: '',
        quantity: 0,
        cost_price: 0,
        retail_price: 0,
        total: 0,
        comments: '',
      };
    case 'AdjustmentsTable':
      return {
        description: '',
        cost_adjustment: 0,
        price_adjustment: 0,
        comments: '',
        total: 0,
      };
    default:
      console.error(`Unknown grid type for new row creation: "${gridType}"`);
      return {};
  }
}