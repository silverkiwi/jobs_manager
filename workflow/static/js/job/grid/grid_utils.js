import { createNewRow } from "../deserialize_job_pricing.js";
import { sections } from "./grid_initialization.js";

export function calculateGridHeight(gridApi, numRows) {
  const rowHeight = gridApi.getSizesForCurrentTheme().rowHeight || 28;
  const headerElement = document.querySelector(".ag-header");
  const headerHeight = headerElement ? headerElement.offsetHeight : 32;

  return numRows * rowHeight + headerHeight;
}

export function calculateTotalRevenue() {
  const revenueTotals = {
    time: { estimate: 0, quote: 0, reality: 0 },
    materials: { estimate: 0, quote: 0, reality: 0 },
    adjustments: { estimate: 0, quote: 0, reality: 0 },
  };

  const gridTypes = ["Time", "Materials", "Adjustments"];

  sections.forEach((section) => {
    gridTypes.forEach((gridType) => {
      const gridKey = `${section}${gridType}Table`;
      const gridData = window.grids[gridKey];
      if (gridData && gridData.api) {
        gridData.api.forEachNode((node) => {
          const rowCost = parseFloat(node.data.cost) || 0;
          const rowRevenue = parseFloat(node.data.revenue) || 0;
          const revenueType = gridType.toLowerCase();
          revenueTotals[revenueType][section] += rowRevenue;
        });
      }
    });
  });

  const revenueGrid = window.grids["revenueTable"];
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
          data.estimate =
            revenueTotals.time.estimate +
            revenueTotals.materials.estimate +
            revenueTotals.adjustments.estimate;
          data.quote =
            revenueTotals.time.quote +
            revenueTotals.materials.quote +
            revenueTotals.adjustments.quote;
          data.reality =
            revenueTotals.time.reality +
            revenueTotals.materials.reality +
            revenueTotals.adjustments.reality;
          break;
      }
    });
  }

  revenueGrid.api.refreshCells();
}

export function calculateTotalCost() {
  const totals = {
    time: { estimate: 0, quote: 0, reality: 0 },
    materials: { estimate: 0, quote: 0, reality: 0 },
    adjustments: { estimate: 0, quote: 0, reality: 0 },
  };

  const gridTypes = ["Time", "Materials", "Adjustments"];

  sections.forEach((section) => {
    gridTypes.forEach((gridType) => {
      const gridKey = `${section}${gridType}Table`;
      const gridData = window.grids[gridKey];
      if (gridData && gridData.api) {
        gridData.api.forEachNode((node) => {
          let rowCost = 0;

          // Different cost calculation for each type
          if (gridType === "Time") {
            // Cost = (minutes * wage_rate) / 60
            const minutes = parseFloat(node.data.total_minutes) || 0;
            const wageRate = parseFloat(node.data.wage_rate) || 0;
            rowCost = (minutes * wageRate) / 60;
          } else if (gridType === "Materials") {
            // Cost = quantity * unit_cost
            const quantity = parseFloat(node.data.quantity) || 0;
            const unitCost = parseFloat(node.data.unit_cost) || 0;
            rowCost = quantity * unitCost;
          } else if (gridType === "Adjustments") {
            // Cost = cost_adjustment
            rowCost = parseFloat(node.data.cost_adjustment) || 0;
          }

          const costType = gridType.toLowerCase();
          totals[costType][section] += rowCost;
        });
      }
    });
  });

  const costGrid = window.grids["costsTable"];
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
          data.estimate =
            totals.time.estimate +
            totals.materials.estimate +
            totals.adjustments.estimate;
          data.quote =
            totals.time.quote +
            totals.materials.quote +
            totals.adjustments.quote;
          data.reality =
            totals.time.reality +
            totals.materials.reality +
            totals.adjustments.reality;
          break;
      }
    });
    costGrid.api.refreshCells();
  }
}

export function onCellKeyDown(params) {
  const isComplex = document.getElementById("complex-job").textContent.toLowerCase() === 'true';

  if (params.event.key === "Enter" && isComplex) {
    const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
    if (isLastRow) {
      const newRow = createNewRow(params.context.gridType);
      if (newRow) {
        params.api.applyTransaction({ add: [newRow] });
        setTimeout(() => {
          params.api.setFocusedCell(params.rowIndex + 1, params.column.colId);
          params.api.startEditingCell({
            rowIndex: params.rowIndex + 1,
            colKey: params.column.colId,
          });
        }, 0);
        adjustGridHeight(params.api, `${gridKey}`);
      }
    }
  }
}

export function calculateRetailRate(costRate, markupRate) {
  return costRate + costRate * markupRate;
}

function fetchMaterialsMarkup(rowData) {
  if (rowData.materialsMarkup !== undefined) {
    return Promise.resolve(rowData.materialsMarkup);
  }

  return fetch("/api/company_defaults")
    .then((response) => response.json())
    .then((companyDefaults) => {
      rowData.materialsMarkup =
        parseFloat(companyDefaults.materials_markup) || 0.2;
      return rowData.materialsMarkup;
    })
    .catch((error) => {
      console.error("Error fetching company defaults:", error);
      return 0.2;
    });
}

export function getRetailRate(params) {
  if (params.data.unit_revenue !== undefined) {
    return params.data.unit_revenue; // Return stored value
  }

  // Fetch markup asynchronously, but return the last known value immediately
  fetchMaterialsMarkup(params.data).then((markupRate) => {
    if (!params.data.isManualOverride) {
      params.data.unit_revenue = calculateRetailRate(
        params.data.unit_cost,
        markupRate,
      );
      params.api.refreshCells({
        rowNodes: [params.node],
        columns: ["unit_revenue"],
        force: true,
      });
    }
  });

  return params.data.unit_revenue || 0; // Default fallback value
}

export function setRetailRate(params) {
  let newValue = parseFloat(params.newValue);
  let costRate = parseFloat(params.data.unit_cost) || 0;

  fetchMaterialsMarkup(params.data).then((markupRate) => {
    if (
      !isNaN(newValue) &&
      newValue !== calculateRetailRate(costRate, markupRate)
    ) {
      params.data.isManualOverride = true;
    }

    if (!params.data.isManualOverride) {
      params.data.unit_revenue = calculateRetailRate(costRate, markupRate);
    } else {
      params.data.unit_revenue = newValue;
    }

    params.api.refreshCells({
      rowNodes: [params.node],
      columns: ["unit_revenue"],
      force: true,
    });
  });

  console.log(`New Retail Rate calculated: ${params.data.unit_revenue}`);

  return true;
}

export function capitalize(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function adjustGridHeight(gridApi, containerId) {
  const container = document.getElementById(containerId);
  if (!container) {
    console.warn(`Grid container #${containerId} not found.`);
    return;
  }

  let rowCount = 0;
  gridApi.forEachNode(() => rowCount++);

  const rowHeight = gridApi.getSizesForCurrentTheme().rowHeight || 28;

  const header = container.querySelector(".ag-header");
  const headerHeight = header ? header.offsetHeight : 32;

  const maxHeight = 360;

  let desiredHeight = rowCount * rowHeight + headerHeight;

  if (desiredHeight > maxHeight) {
    desiredHeight = maxHeight;
  }

  container.style.height = `${desiredHeight}px`;
}
