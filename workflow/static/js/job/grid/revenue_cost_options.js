import { sections } from "./grid_initialization.js";
import {
  calculateTotalRevenue,
  calculateTotalCost,
  capitalize,
} from "./grid_utils.js";
import { currencyFormatter } from "./parsers.js";
import { Environment } from "../../env.js";

// Grid options for Totals table (default 4 rows, autoHeight for proper resizing)
export function createRevenueGridOptions() {
  return {
    columnDefs: [
      { headerName: "Category", field: "category", editable: false },
      {
        headerName: "Estimate",
        field: "estimate",
        editable: false,
        valueFormatter: currencyFormatter,
      },
      {
        headerName: "Quote",
        field: "quote",
        editable: false,
        valueFormatter: currencyFormatter,
      },
      {
        headerName: "Reality",
        field: "reality",
        editable: false,
        valueFormatter: currencyFormatter,
      },
    ],
    rowData: [
      { category: "Total Time", estimate: 0, quote: 0, reality: 0 },
      { category: "Total Materials", estimate: 0, quote: 0, reality: 0 },
      { category: "Total Adjustments", estimate: 0, quote: 0, reality: 0 },
      { category: "Total Project Revenue", estimate: 0, quote: 0, reality: 0 },
    ], // Default 4 rows
    domLayout: "autoHeight",
    rowHeight: 28,
    headerHeight: 32,
    suppressPaginationPanel: true,
    suppressHorizontalScroll: true,
    onGridReady: (params) => {
      window.grids["revenueTable"] = {
        gridInstance: params.api,
        api: params.api,
      };
      params.api.sizeColumnsToFit();

      calculateTotalRevenue();
    },
    onGridSizeChanged: (params) => {
      params.api.sizeColumnsToFit();
    },
    autoSizeStrategy: {
      type: "fitCellContents",
    },
  };
}

export function createCostGridOptions() {
  return {
    columnDefs: [
      { headerName: "Category", field: "category", editable: false },
      {
        headerName: "Estimate",
        field: "estimate",
        editable: false,
        valueFormatter: currencyFormatter,
      },
      {
        headerName: "Quote",
        field: "quote",
        editable: false,
        valueFormatter: currencyFormatter,
      },
      {
        headerName: "Reality",
        field: "reality",
        editable: false,
        valueFormatter: currencyFormatter,
      },
    ],
    rowData: [
      { category: "Total Time", estimate: 0, quote: 0, reality: 0 },
      { category: "Total Materials", estimate: 0, quote: 0, reality: 0 },
      { category: "Total Adjustments", estimate: 0, quote: 0, reality: 0 },
      { category: "Total Project Cost", estimate: 0, quote: 0, reality: 0 },
    ], // Default 4 rows
    domLayout: "autoHeight",
    rowHeight: 28,
    headerHeight: 32,
    suppressPaginationPanel: true,
    suppressHorizontalScroll: true,
    onGridReady: (params) => {
      window.grids["costsTable"] = {
        gridInstance: params.api,
        api: params.api,
      };
      params.api.sizeColumnsToFit();

      calculateTotalCost();
    },
    onGridSizeChanged: (params) => {
      params.api.sizeColumnsToFit();
    },
    autoSizeStrategy: {
      type: "fitCellContents",
    },
  };
}

/**
 * Recalcula cost_of_time e value_of_time de uma row simples de Time,
 * usando hours * wage_rate e hours * charge_out_rate.
 */
export function recalcSimpleTimeRow(row) {
  const hours = parseFloat(row.hours) || 0;
  const wage = parseFloat(row.wage_rate) || 0;
  const charge = parseFloat(row.charge_out_rate) || 0;

  row.cost_of_time = hours * wage;
  row.value_of_time = hours * charge;
}

/**
 * Calcula os totais (cost, retail) para cada seção (estimate, quote, reality)
 * e atualiza a SimpleTotalsTable correspondente.
 */
export function calculateSimpleTotals() {
  const simpleTotals = {
    estimate: { cost: 0, retail: 0 },
    quote: { cost: 0, retail: 0 },
    reality: { cost: 0, retail: 0 },
  };

  if (Environment.isDebugMode()) {
    console.log("Starting calculateSimpleTotals calculation");
  }

  sections.forEach((section) => {
    if (Environment.isDebugMode()) {
      console.log(`Processing section: ${section}`);
    }

    // 1) Time
    {
      const timeGridKey = `simple${capitalize(section)}TimeTable`;
      const timeApi = window.grids[timeGridKey]?.api;
      if (timeApi) {
        const updatedTimeRows = [];
        timeApi.forEachNode((node) => {
          recalcSimpleTimeRow(node.data);

          updatedTimeRows.push(node.data);

          const cost = parseFloat(node.data.cost_of_time) || 0;
          const retail = parseFloat(node.data.value_of_time) || 0;
          simpleTotals[section].cost += cost;
          simpleTotals[section].retail += retail;
        });

        if (updatedTimeRows.length > 0) {
          timeApi.applyTransaction({ update: updatedTimeRows });
        }

        if (Environment.isDebugMode()) {
          console.log(`Time totals for ${section}:`, {
            cost: simpleTotals[section].cost,
            retail: simpleTotals[section].retail,
          });
        }
      }
    }

    // 2) Materials
    {
      const matGridKey = `simple${capitalize(section)}MaterialsTable`;
      const matApi = window.grids[matGridKey]?.api;
      if (matApi) {
        matApi.forEachNode((node) => {
          const cost = parseFloat(node.data.material_cost) || 0;
          const retail = parseFloat(node.data.retail_price) || 0;
          simpleTotals[section].cost += cost;
          simpleTotals[section].retail += retail;
        });
        if (Environment.isDebugMode()) {
          console.log(`Materials totals for ${section}:`, {
            cost: simpleTotals[section].cost,
            retail: simpleTotals[section].retail,
          });
        }
      }
    }

    // 3) Adjustments
    {
      const adjGridKey = `simple${capitalize(section)}AdjustmentsTable`;
      const adjApi = window.grids[adjGridKey]?.api;
      if (adjApi) {
        adjApi.forEachNode((node) => {
          const costAdj = parseFloat(node.data.cost_adjustment) || 0;
          const priceAdj = parseFloat(node.data.price_adjustment) || 0;
          simpleTotals[section].cost += costAdj;
          simpleTotals[section].retail += priceAdj;
        });
        if (Environment.isDebugMode()) {
          console.log(`Adjustments totals for ${section}:`, {
            cost: simpleTotals[section].cost,
            retail: simpleTotals[section].retail,
          });
        }
      }
    }
  });

  sections.forEach((section) => {
    const stKey = `simple${capitalize(section)}TotalsTable`;
    const stGrid = window.grids[stKey];
    if (stGrid && stGrid.api) {
      const rowUpdates = [];
      stGrid.api.forEachNode((node) => {
        node.data.cost = simpleTotals[section].cost;
        node.data.retail = simpleTotals[section].retail;
        rowUpdates.push(node.data);
      });

      if (rowUpdates.length > 0) {
        stGrid.api.applyTransaction({ update: rowUpdates });
      }

      if (Environment.isDebugMode()) {
        console.log(`Final totals for ${section}:`, {
          cost: simpleTotals[section].cost,
          retail: simpleTotals[section].retail,
        });
      }
    }
  });

  if (Environment.isDebugMode()) {
    console.log("Completed calculateSimpleTotals calculation", simpleTotals);
  }
}
