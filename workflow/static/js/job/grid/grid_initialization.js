/**
 * @fileoverview Grid initialization and management module for job pricing system
 * @module job_pricing_grids
 */

import { createNewRow, getGridData } from "../deserialize_job_pricing.js";

import { capitalize } from "./grid_utils.js";

/** @constant {string[]} sections - Available pricing sections */
export const sections = ["estimate", "quote", "reality"];

/** @constant {string[]} workType - Types of work that can be priced */
const workType = ["Time", "Materials", "Adjustments"];

/**
 * Initializes simple grid views
 * @param {Object} commonGridOptions - Common configuration options for all grids
 * @param {Object} timeGridOptions - Configuration specific to time grids
 * @param {Object} materialsGridOptions - Configuration specific to materials grids
 * @param {Object} adjustmentsGridOptions - Configuration specific to adjustments grids
 */
export function initializeSimpleGrids(
  commonGridOptions,
  timeGridOptions,
  materialsGridOptions,
  adjustmentsGridOptions,
) {
  sections.forEach(section => {
    workType.forEach(work => {
      console.log(`Creating simple grid for section: ${section}, work type: ${work}`);

      const gridType = `Simple${work}Table`;
      const gridKey = `simple${capitalize(section)}${work}Table`;

      const gridElement = document.querySelector(`#${gridKey}`);
      console.log(`Grid element found for key: ${gridKey}`, gridElement);

      if (!gridKey) {
        console.error(`Grid element not found for key: ${gridKey}`);
        return;
      }

      let specificGridOptions;
      switch (work) {
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
      console.log(`Specific grid options retrieved for ${gridType}:`, specificGridOptions);

      const rowData = getInitialRowData(section, gridType);
      console.log(`Initial row data loaded for ${gridKey}:`, rowData);

      const gridOptions = {
        ...specificGridOptions,
        context: {
          section,
          gridType: gridType,
          gridKey: gridKey,
        },
        rowData: rowData,
      };
      console.log(`Combined grid options created for ${gridKey}:`, gridOptions);

      console.log(`Creating simple grid for: ${gridKey}`);
      const gridInstance = agGrid.createGrid(gridElement, gridOptions);
      console.log(`Grid instance created for ${gridKey}:`, gridInstance);

      gridInstance.setGridOption('rowData', rowData);
      console.log(`Row data set for ${gridKey}`);
    });
  });

  console.log('Simple grid initialization complete');
}

/**
 * Initializes advanced grid views with full functionality
 * @param {Object} commonGridOptions - Common configuration options for all grids
 * @param {Object} timeGridOptions - Configuration specific to time grids
 * @param {Object} materialsGridOptions - Configuration specific to materials grids
 * @param {Object} adjustmentsGridOptions - Configuration specific to adjustments grids
 */
export function initializeAdvancedGrids(
  commonGridOptions,
  timeGridOptions,
  materialsGridOptions,
  adjustmentsGridOptions,
) {
  window.grids = {};

  console.log("Starting grid initialization...");
  console.log("Common grid options:", commonGridOptions);
  console.log("Time grid options:", timeGridOptions); 
  console.log("Materials grid options:", materialsGridOptions);
  console.log("Adjustments grid options:", adjustmentsGridOptions);

  sections.forEach((section) => {
    console.log(`Initializing grids for section: ${section}`);
    workType.forEach((work) => {
      console.log(`Creating grid for ${section} ${work}`);
      console.log("Grid options for this iteration:");
      console.log(`commonGridOptions:`, commonGridOptions);
      console.log(`timeGridOptions:`, timeGridOptions);
      console.log("materialsGridOptions:", materialsGridOptions);
      console.log(`adjustmentsGridOptions:`, adjustmentsGridOptions);
      createGrid(
        section,
        work,
        commonGridOptions,
        timeGridOptions,
        materialsGridOptions,
        adjustmentsGridOptions,
      );
      console.log(`Completed creating grid for ${section} ${work}`);
    });
    console.log(`Completed all grids for section: ${section}`);
  });

  console.log("Grid initialization complete");
  console.log("Total grids created:", Object.keys(window.grids).length);
}

/**
 * Creates an individual grid instance
 * @param {string} section - The pricing section (estimate/quote/reality)
 * @param {string} work - The type of work (Time/Materials/Adjustments)
 * @param {Object} commonGridOptions - Common grid configuration
 * @param {Object} timeGridOptions - Time grid specific configuration
 * @param {Object} materialsGridOptions - Materials grid specific configuration
 * @param {Object} adjustmentsGridOptions - Adjustments grid specific configuration
 * @private
 */
function createGrid(
  section,
  work,
  commonGridOptions,
  timeGridOptions,
  materialsGridOptions,
  adjustmentsGridOptions,
) {
  console.log(`Creating grid for section: ${section}, work type: ${work}`);
  
  const gridType = `${work}Table`;
  const gridKey = `${section}${gridType}`;
  const gridElement = document.querySelector(`#${gridKey}`);

  console.log(`Grid element found for key: ${gridKey}`, gridElement);

  const specificGridOptions = getSpecificGridOptions(
    section,
    work,
    gridType,
    timeGridOptions,
    materialsGridOptions,
    adjustmentsGridOptions,
  );
  console.log(`Specific grid options retrieved for ${gridType}:`, specificGridOptions);

  const rowData = getInitialRowData(section, gridType);
  console.log(`Initial row data loaded for ${gridKey}:`, rowData);

  const gridOptions = createGridOptions(
    section,
    gridType,
    gridKey,
    commonGridOptions,
    specificGridOptions,
    rowData,
  );
  console.log(`Combined grid options created for ${gridKey}:`, gridOptions);

  const gridInstance = agGrid.createGrid(gridElement, gridOptions);
  console.log(`Grid instance created for ${gridKey}:`, gridInstance);

  gridInstance.setGridOption("rowData", rowData);
  console.log(`Row data set for ${gridKey}`);
}

/**
 * Retrieves specific grid options based on grid type
 * @param {string} section - The pricing section
 * @param {string} work - The type of work
 * @param {string} gridType - The type of grid
 * @param {Object} timeGridOptions - Time grid configuration
 * @param {Object} materialsGridOptions - Materials grid configuration
 * @param {Object} adjustmentsGridOptions - Adjustments grid configuration
 * @returns {Object} The specific grid options
 * @private
 */
function getSpecificGridOptions(
  section,
  work,
  gridType,
  timeGridOptions,
  materialsGridOptions,
  adjustmentsGridOptions,
) {
  let specificGridOptions;

  switch (gridType) {
    case "TimeTable":
      specificGridOptions = getTimeTableOptions(section, timeGridOptions);
      break;
    case "MaterialsTable":
      specificGridOptions = materialsGridOptions;
      break;
    case "AdjustmentsTable":
      specificGridOptions = adjustmentsGridOptions;
      break;
  }

  return specificGridOptions;
}

/**
 * Gets time table specific options based on section
 * @param {string} section - The pricing section
 * @param {Object} timeGridOptions - Base time grid options
 * @returns {Object} Modified time grid options
 * @private
 */
function getTimeTableOptions(section, timeGridOptions) {
  if (section === "reality") {
    return createRealityTimeTableOptions(timeGridOptions);
  }
  return createRegularTimeTableOptions(timeGridOptions);
}

/**
 * Creates options specific to reality time tables
 * @param {Object} timeGridOptions - Base time grid options
 * @returns {Object} Modified options for reality time tables
 * @private
 */
function createRealityTimeTableOptions(timeGridOptions) {
  const options = JSON.parse(JSON.stringify(timeGridOptions));
  options.columnDefs.forEach((col) => {
    col.editable = false;
    if (col.field === "link") {
      col.cellRenderer = timeGridOptions.columnDefs.find(
        (c) => c.field === "link",
      ).cellRenderer;
    }
  });
  options.columnDefs = options.columnDefs.filter((col) => col.field !== "");
  return options;
}

/**
 * Creates options for regular time tables
 * @param {Object} timeGridOptions - Base time grid options
 * @returns {Object} Modified options for regular time tables
 * @private
 */
function createRegularTimeTableOptions(timeGridOptions) {
  const options = { ...timeGridOptions };
  options.columnDefs = options.columnDefs.map((col) => {
    if (col.field === "link") {
      return { ...col, hide: true };
    }
    return col;
  });
  return options;
}

/**
 * Gets initial row data for a grid
 * @param {string} section - The pricing section
 * @param {string} gridType - The type of grid
 * @returns {Array} Initial row data
 * @throws {Error} If pricing data is not loaded
 * @private
 */
function getInitialRowData(section, gridType) {
  if (!latest_job_pricings_json) {
    throw new Error(
      "latest_job_pricings_json must be loaded before grid initialization",
    );
  }

  const sectionData = latest_job_pricings_json[`${section}_pricing`];
  if (!sectionData) {
    console.warn(
      `Data not found for section '${section}'. Assuming this is a new job.`,
    );
  }

  let rowData = getGridData(section, gridType);
  if (rowData.length === 0) {
    rowData = [createNewRow(gridType)];
  }

  return rowData;
}

/**
 * Creates combined grid options
 * @param {string} section - The pricing section
 * @param {string} gridType - The type of grid
 * @param {string} gridKey - Unique grid identifier
 * @param {Object} commonGridOptions - Common grid options
 * @param {Object} specificGridOptions - Grid type specific options
 * @param {Array} rowData - Initial row data
 * @returns {Object} Combined grid options
 * @private
 */
function createGridOptions(
  section,
  gridType,
  gridKey,
  commonGridOptions,
  specificGridOptions,
  rowData,
) {
  return {
    ...commonGridOptions,
    ...specificGridOptions,
    context: {
      section,
      gridType: `${gridType}`,
      gridKey: gridKey,
    },
    rowData: rowData,
  };
}

/**
 * Creates revenue and cost summary tables
 * @param {Object} revenueGridOptions - Configuration for revenue table
 * @param {Object} costGridOptions - Configuration for cost table
 */
export function createTotalTables(revenueGridOptions, costGridOptions) {
  const revenueTableEl = document.querySelector("#revenueTable");
  if (revenueTableEl) {
    try {
      agGrid.createGrid(revenueTableEl, revenueGridOptions);
    } catch (error) {
      console.error("Error initializing revenue table:", error);
    }
  } else {
    console.error("Revenue table element not found");
  }

  const costsTableEl = document.querySelector("#costsTable");
  if (costsTableEl) {
    try {
      agGrid.createGrid(costsTableEl, costGridOptions);
    } catch (error) {
      console.error("Error initializing costs table:", error);
    }
  } else {
    console.error("Costs table element not found");
  }
}

/**
 * Verifies that all expected grids were properly initialized
 */
export function checkGridInitialization() {
  const expectedGridCount = sections.length * workType.length + 2;
  const actualGridCount = Object.keys(window.grids).length;

  if (actualGridCount !== expectedGridCount) {
    console.error(
      `Not all grids were initialized. Expected: ${expectedGridCount}, Actual: ${actualGridCount}`,
    );
  } else {
    console.log("All grids successfully initialized.");
  }
}
