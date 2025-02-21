// Deserialize entryFormsData
document.addEventListener("DOMContentLoaded", function () {
  // Update the HTML element ID to match the backend context
  const latestJobPricingsElement = document.getElementById(
    "latestJobPricingsData",
  );
  if (latestJobPricingsElement) {
    try {
      // Log raw content to debug
      console.log(
        "Debug: Raw latestJobPricingsData content:",
        latestJobPricingsElement.textContent,
      );
      // Use snake case for consistency with backend variable names
      window.latest_job_pricings_json = JSON.parse(
        latestJobPricingsElement.textContent,
      );
      console.log(
        "Debug: Loaded latest job pricing data:",
        window.latest_job_pricings_json,
      );
    } catch (error) {
      console.error("Failed to parse latest job pricing data:", error);
    }
  } else {
    console.error("Could not find latest job pricing data.");
  }
});

document.addEventListener("DOMContentLoaded", function () {
  // Update the HTML element ID to match the backend context
  const historicalJobPricingsElement = document.getElementById(
    "historicalJobPricingsData",
  );
  if (historicalJobPricingsElement) {
    try {
      // Log raw content to debug
      console.log(
        "Debug: Raw historicalJobPricingsElement content:",
        historicalJobPricingsElement.textContent,
      );
      // Use snake case for consistency with backend variable names
      window.historical_job_pricings_json = JSON.parse(
        historicalJobPricingsElement.textContent,
      );
      console.log(
        "Debug: Loaded historical job pricing data:",
        window.historical_job_pricings_json,
      );
    } catch (error) {
      console.error("Failed to parse Historical job pricing data:", error);
    }
  } else {
    console.error("Could not find historical job pricing data.");
  }
});

export function getGridData(section, gridType) {
  console.log("Debug: getGridData called with:", { section, gridType });
  console.log("Debug: Current window context:", window);

  // Check if latest_job_pricings_json data is available globally
  if (!window.latest_job_pricings_json) {
    console.error("Error: latest_job_pricings_json data is not loaded.");
    console.log("Debug: Window state:", {
      hasLatestPricings: !!window.latest_job_pricings_json,
      windowKeys: Object.keys(window)
    });
    return [createNewRow(gridType)];
  }

  console.log(
    "Debug: About to access latest job pricing data:",
    window.latest_job_pricings_json,
  );

  // Update to use the correct field names (_pricing suffix)
  const sectionKey = `${section}_pricing`;
  console.log("Debug: Looking for section:", sectionKey);
  console.log("Debug: Available sections:", 
    Object.keys(window.latest_job_pricings_json)
  );

  // Validate if the requested section exists in latest_job_pricings_json
  const sectionData = window.latest_job_pricings_json[sectionKey];
  console.log("Debug: Found section data:", sectionData);
  console.log("Debug: Section data structure:", 
    sectionData ? Object.keys(sectionData) : "No section data"
  );

  let realGridType = gridType;

  if (gridType.startsWith("Simple")) {
    realGridType = gridType.replace("Simple", "");
    console.log("Debug: Converted simple grid type to:", realGridType);
  }

  // Convert grid type to entry type
  const gridBaseName = realGridType.toLowerCase().replace("table", "");
  const entryType =
    (gridBaseName === "materials"
      ? "material"
      : gridBaseName === "adjustments"
        ? "adjustment"
        : gridBaseName) + "_entries";
  console.log("Debug: Looking for entry type:", entryType);
  console.log("Debug: Grid type conversion:", {
    original: gridType,
    realGridType,
    gridBaseName,
    entryType
  });

  if (!sectionData || sectionData[entryType].length === 0) {
    console.log(
      `Debug: No data found for section "${sectionKey}" and entry type "${entryType}". Creating a new row.`,
    );
    console.log("Debug: Available entry types:", 
      sectionData ? Object.keys(sectionData) : "No section data"
    );
    return [createNewRow(gridType)];
  }

  console.log("Debug: Found entries:", sectionData[entryType]);
  console.log("Debug: Number of entries found:", sectionData[entryType].length);
  console.log("Debug: First entry sample:", 
    sectionData[entryType][0] ? JSON.stringify(sectionData[entryType][0], null, 2) : "No entries"
  );

  // Return the existing entries for the section and gridType
  return loadExistingJobEntries(sectionData[entryType], gridType);
}

function loadExistingJobEntries(entries, gridType) {
  switch (gridType) {

    // First, we switch through the advanced cases
    case "TimeTable":
      return loadAdvJobTime(entries);
    case "MaterialsTable":
      return loadAdvJobMaterial(entries);
    case "AdjustmentsTable":
      return loadAdvJobAdjustment(entries);

    // Second, we switch through the simple ones
    case "SimpleTimeTable":
      return loadSimpleJobTime(entries);
    case "SimpleMaterialsTable":
      return loadSimpleJobMaterial(entries);
    case "SimpleAdjustmentsTable":
      return loadSimpleJobAdjustment(entries);
    default:
      console.error(`Unknown grid type: "${gridType}"`);
      return [createNewRow(gridType)];
  }
}

function loadAdvJobTime(entries) {
  return entries.map((entry) => {
    const hours = (entry.total_minutes / 60).toFixed(1); // Convert minutes to hours with one decimal
    const formattedTotalMinutes = `${entry.total_minutes} (${hours} hours)`; // Include total minutes and decimal hours

    return {
      description: entry.description,
      items: entry.items,
      mins_per_item: entry.minutes_per_item,
      wage_rate: entry.wage_rate,
      charge_out_rate: entry.charge_out_rate,
      total_minutes: formattedTotalMinutes,
      revenue: entry.revenue,
      link:
        entry.timesheet_date && entry.staff_id
          ? `/timesheets/day/${entry.timesheet_date}/${entry.staff_id}`
          : "/timesheets/overview/",
    };
  });
}

function loadAdvJobMaterial(entries) {
  console.log(`Debug: Found ${entries.length} material entries.`);
  return entries.map((entry) => ({
    item_code: entry.item_code,
    description: entry.description,
    quantity: entry.quantity,
    unit_cost: entry.unit_cost,
    unit_revenue: entry.unit_revenue,
    revenue: entry.revenue,
    comments: entry.comments,
  }));
}

function loadAdvJobAdjustment(entries) {
  console.log(`Debug: Found ${entries.length} adjustment entries.`);
  return entries.map((entry) => ({
    description: entry.description,
    cost_adjustment: entry.cost_adjustment,
    price_adjustment: entry.price_adjustment,
    comments: entry.comments,
    revenue: entry.revenue,
  }));
}

function loadSimpleJobTime(entries) {
  let totalMinutes = 0;

  entries.forEach(e => {
    totalMinutes += (e.total_minutes || 0);
  });

  const hours = +(totalMinutes / 60).toFixed(1);

  return entries.map((entry) => ({
    description: entry.description,
    hours: hours,
    cost_of_time: entry.wage_rate,
    value_of_time: entry.wage_rate * hours,
    charge_out_rate: entry.charge_out_rate,
  }));
}

function loadSimpleJobMaterial(entries) {
  return entries.map((entry) => ({
    description: entry.description,
    material_cost: entry.unit_cost * entry.quantity,
    retail_price: entry.unit_revenue * entry.quantity
  }));
}

function loadSimpleJobAdjustment(entries) {
  return entries.map((entry) => ({
    cost: entry.cost_adjustment,
    retail: entry.price_adjustment
  }));
}

export function createNewRow(gridType) {
  console.log("Debug: Creating new row for grid type:", gridType);
  
  const companyDefaults = document.getElementById("companyDefaults");
  console.log("Debug: Company defaults element:", companyDefaults);
  
  const defaultWageRate = parseFloat(companyDefaults.dataset.wageRate);
  const defaultChargeOutRate = parseFloat(
    companyDefaults.dataset.chargeOutRate,
  );
  console.log("Debug: Default rates:", {defaultWageRate, defaultChargeOutRate});

  let newRow;
  switch (gridType) {

    // 1) First, we switch through the advanced tables
    case "TimeTable":
      newRow = {
        description: "",
        items: 1,
        mins_per_item: 0,
        wage_rate: defaultWageRate,
        charge_out_rate: defaultChargeOutRate,
        total_minutes: 0,
        total_minutes_display: "0 (0.0 hours)",
        revenue: 0,
      };
      console.log("Debug: Created new TimeTable row:", newRow);
      return newRow;
      
    case "MaterialsTable":
      newRow = {
        item_code: "",
        description: "",
        quantity: 0,
        unit_cost: 0,
        unit_revenue: 0,
        isManualOverride: false,
        revenue: 0,
        comments: "",
      };
      console.log("Debug: Created new MaterialsTable row:", newRow);
      return newRow;
      
    case "AdjustmentsTable":
      newRow = {
        description: "",
        cost_adjustment: 0,
        price_adjustment: 0,
        comments: "",
        revenue: 0,
      };
      console.log("Debug: Created new AdjustmentsTable row:", newRow);
      return newRow;

    // 2) Second, we switch through the simple tables
    case "SimpleTimeTable":
      newRow = {
        description: "Single time entry",
        hours: 0,
        cost_of_time: 0,
        value_of_time: 0,
        wage_rate: defaultWageRate,
        charge_out_rate: defaultChargeOutRate
      };
      console.log("Debug: Created new SimpleTimeTable row:", newRow);
      return newRow;
      
    case "SimpleMaterialsTable":
      newRow = {
        description: "Single materials entry",
        material_cost: 0,
        retail_price: 0
      };
      console.log("Debug: Created new SimpleMaterialsTable row:", newRow);
      return newRow;
      
    case "SimpleAdjustmentsTable":
      newRow = {
        description: "Single adjustment entry",
        cost_adjustment: 0,
        price_adjustment: 0
      };
      console.log("Debug: Created new SimpleAdjustmentsTable row:", newRow);
      return newRow;
      
    case "SimpleTotalTable":
      newRow = {
        cost: 0,
        retail: 0
      };
      console.log("Debug: Created new SimpleTotalTable row:", newRow);
      return newRow;
      
    default:
      console.error(`Unknown grid type for new row creation: "${gridType}"`);
      return {};
  }
}
