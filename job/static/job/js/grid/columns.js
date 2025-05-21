import { calculateTotalRevenue } from "./grid_utils.js";
import { Environment } from "/static/js/env.js";

function deleteIconCellRenderer(params) {
  const isLastRow = params.api.getDisplayedRowCount() === 1;
  const iconClass = isLastRow ? "delete-icon disabled" : "delete-icon";
  return `<span class='${iconClass}'>🗑️</span>`;
}

function onDeleteIconClicked(params) {}

export function createTrashCanColumn() {
  return {
    headerName: "",
    field: "",
    maxWidth: 30,
    cellRenderer: deleteIconCellRenderer,
    onCellClicked: (params) => {
      if (params.api.getDisplayedRowCount() > 1) {
        if (Environment.isDebugMode()) {
          console.log("Deleting row:", params.node.data);
        }
        params.api.applyTransaction({ remove: [params.node.data] });
        if (Environment.isDebugMode()) {
          console.log("Row deleted, recalculating totals");
        }
        calculateTotalRevenue(); // Recalculate totals after row deletion
      }
    },
    cellStyle: {
      display: "flex",
      alignItems: "center",
      justifyContent: "flex-end",
      padding: 0,
    },
  };
}
