document.addEventListener("DOMContentLoaded", function () {
  const container = document.getElementById("deliveryReceiptContainer");
  const STOCK_HOLDING_JOB_ID = container.dataset.stockHoldingJobId;
  const STOCK_HOLDING_JOB_NAME = container.dataset.stockHoldingJobName;
  const JOB_LIST = document.getElementById("job-list-data").textContent;

  // Parse the job list from the data attribute
  let ALLOCATABLE_JOBS = [];
  try {
    ALLOCATABLE_JOBS = JSON.parse(JOB_LIST);
  } catch (e) {
    console.error("Failed to parse job list data:", e);
    // Handle error - maybe disable allocation?
  }

  // Select All checkboxes
  const selectAllPending = document.getElementById("selectAllPending");
  const selectAllReceived = document.getElementById("selectAllReceived");
  // Removed static NodeList declarations for pendingCheckboxes and receivedCheckboxes

  selectAllPending.addEventListener("change", function () {
    // Query dynamically inside the handler
    document
      .querySelectorAll("#pendingItems .line-checkbox")
      .forEach((checkbox) => {
        checkbox.checked = this.checked;
      });
  });

  selectAllReceived.addEventListener("change", function () {
    // Query dynamically inside the handler
    document
      .querySelectorAll("#receivedItems .line-checkbox")
      .forEach((checkbox) => {
        checkbox.checked = this.checked;
      });
  });

  // Move Selected buttons
  document
    .getElementById("moveSelectedToReceived")
    .addEventListener("click", function () {
      // Query for currently checked checkboxes in the pending table
      document
        .querySelectorAll("#pendingItems .line-checkbox:checked")
        .forEach((checkbox) => {
          const row = checkbox.closest("tr"); // More reliable way to get the row
          if (row) {
            // Check if row was found
            const orderedQtyCell = row.querySelector("td:nth-child(4)"); // Get the specific cell
            if (orderedQtyCell) {
              // Check if cell exists
              const orderedQty = parseInt(orderedQtyCell.textContent);
              moveRowToReceived(row, orderedQty);
            } else {
              console.error(
                "Could not find ordered quantity cell for pending row:",
                row,
              );
            }
          } else {
            console.error(
              "Could not find row for checked pending checkbox:",
              checkbox,
            );
          }
        });
    });

  document
    .getElementById("moveAllToReceived")
    .addEventListener("click", function () {
      // Query for all rows in the pending table
      document
        .querySelectorAll("#pendingItems tr[data-line-id]")
        .forEach((row) => {
          const lineId = row.dataset.lineId;
          // No need to check checkbox, move all
          const orderedQtyCell = row.querySelector("td:nth-child(4)"); // Get the specific cell
          if (orderedQtyCell) {
            // Check if cell exists
            const orderedQty = parseInt(orderedQtyCell.textContent);
            moveRowToReceived(row, orderedQty);
          } else {
            console.error(
              "Could not find ordered quantity cell for pending row:",
              row,
            );
          }
        });
    });

  document
    .getElementById("moveSelectedToPending")
    .addEventListener("click", function () {
      // Query for currently checked checkboxes in the received table
      document
        .querySelectorAll("#receivedItems .line-checkbox:checked")
        .forEach((checkbox) => {
          const lineId = checkbox.dataset.lineId;
          const row = checkbox.closest("tr"); // More reliable way to get the row
          if (row) {
            moveRowToPending(row);
          } else {
            console.error(
              "Could not find row for checked received checkbox:",
              checkbox,
            );
          }
        });
    });

  document
    .getElementById("moveAllToPending")
    .addEventListener("click", function () {
      // Query for all rows in the received table
      document
        .querySelectorAll("#receivedItems tr[data-line-id]")
        .forEach((row) => {
          const lineId = row.dataset.lineId;
          // No need to check checkbox, move all
          moveRowToPending(row);
        });
    });

  // Helper functions
  function moveRowToReceived(row, orderedQty) {
    const tbody = document.getElementById("receivedItems");
    const lineId = row.dataset.lineId; // Get lineId from original row

    // Check if the row is already in the target table
    if (tbody.querySelector(`tr[data-line-id="${lineId}"]`)) {
      console.warn(`Row ${lineId} already in receivedItems. Skipping move.`);
      return;
    }

    // Clone the basic row structure (we'll modify cells)
    const newRow = row.cloneNode(true);
    // Clear existing content except checkbox cell if needed, or rebuild
    while (newRow.cells.length > 1) {
      // Keep checkbox cell
      newRow.deleteCell(1);
    }

    // --- Rebuild cells according to the new structure ---

    // Get data from original row and global stock job constants
    const originalPoLineJobId = row.dataset.lineJobId || "";
    const originalPoLineJobName = row.dataset.lineJobName || "";
    const description = row.dataset.lineDescription;
    const unitCost = row.dataset.unitCost || "0.00";
    
    const metalType = row.dataset.metalType || "unspecified";
    const alloy = row.dataset.alloy || "";
    const specifics = row.dataset.specifics || "";
    const location = row.dataset.location || "";
    
    newRow.dataset.metalType = metalType;
    newRow.dataset.alloy = alloy;
    newRow.dataset.specifics = specifics;
    newRow.dataset.location = location;
    newRow.dataset.lineDescription = description;

    // Determine the default allocation target
    const defaultTargetJobId = originalPoLineJobId || STOCK_HOLDING_JOB_ID;
    const defaultTargetJobName =
      originalPoLineJobName || STOCK_HOLDING_JOB_NAME;

    // 2. Job Cell (Display Only - Shows original intended job from PO)
    const jobCell = newRow.insertCell();
    jobCell.textContent = originalPoLineJobName || "N/A"; // Show original PO line job or N/A

    // 3. Description Cell
    const descCell = newRow.insertCell();
    descCell.textContent = description;

    // 4. Ordered Cell
    const orderedCell = newRow.insertCell();
    orderedCell.textContent = orderedQty;

    // 5. Total Received Cell (Input)
    const totalReceivedCell = newRow.insertCell();
    totalReceivedCell.innerHTML = `<input type="number" class="form-control form-control-sm total-received-qty"
                                              value="${orderedQty}" min="0"
                                              data-line-id="${lineId}" step="any" required>`; // Default to ordered qty

    // 6. Job Portion Cell (simplified)
    const jobPortioncell = newRow.insertCell();
    jobPortioncell.innerHTML = `
      <input type="number" class="form-control form-control-sm job-allocation-qty"
        value="${orderedQty}" min="0" max="${orderedQty}"
        data-line-id="${lineId}" step="any" required>
      <small class="text-muted">The rest will go to stock</small>
      `;

    // 7. Unit Cost Cell
    const costCell = newRow.insertCell();
    costCell.textContent = `$${unitCost}`;

    // 8. Retail Rate Cell (New)
    const retailRateCell = newRow.insertCell();
    retailRateCell.innerHTML = `
      <input type="number" class="form-control form-control-sm retail-rate"
        value="20" min="0" max="100" step="1"
        data-line-id="${lineId}">
    `;

    // Append the fully constructed row
    tbody.appendChild(newRow);
    row.remove(); // Remove original row from pending
  }

  function moveRowToPending(row) {
    const tbody = document.getElementById("pendingItems");
    // Check if the row is already in the target table (prevent infinite loops if clicked fast)
    if (tbody.querySelector(`tr[data-line-id="${row.dataset.lineId}"]`)) {
      console.warn(
        `Row ${row.dataset.lineId} already in pendingItems. Skipping move.`,
      );
      return;
    }
    const newRow = row.cloneNode(true);
    // Remove received quantity cell (should be 5th cell in received table row)
    const receivedCell = newRow.querySelector("td:nth-child(5)");
    if (receivedCell && receivedCell.querySelector(".received-qty")) {
      // Check it's the correct cell
      newRow.removeChild(receivedCell);
    } else {
      console.warn(
        "Could not find 5th cell (received qty) to remove, or it was already removed:",
        newRow,
      );
    }

    tbody.appendChild(newRow);
    row.remove();
  }

  function collectDeliveryData() {
    const lineAllocationsData = {};

    allLineIds.forEach((lineId) => {
      const receivedRow = document.querySelector(`#receivedItems tr[data-line-id="${lineId}"]`);

      if (receivedRow) {
        const totalReceivedInput = receivedRow.querySelector(".total-received-qty");
        const jobAllocationInput = receivedRow.querySelector(".job-allocation-qty");
        const retailRateInput = receivedRow.querySelector(".retail-rate");
        const totalReceived = parseFloat(totalReceivedInput.value || 0);
        const jobAllocation = parseFloat(jobAllocationInput.value || 0);
        const retailRate = parseFloat(retailRateInput.value || 20);

        const stockAllocation = totalReceived - jobAllocation;

        const jobId = receivedRow.dataset.lineJobId;
        const jobName = receivedRow.dataset.lineJobName;

        const description = receivedRow.dataset.lineDescription;
        const unitCost = receivedRow.dataset.unitCost;
        const metalType = receivedRow.dataset.metalType || "unspecified";
        const alloy = receivedRow.dataset.alloy || "";
        const specifics = receivedRow.dataset.specifics || "";
        const location = receivedRow.dataset.location || "";

        lineAllocationsData[lineId] = {
          total_received: totalReceived,
          job_allocation: jobAllocation,
          stock_allocation: stockAllocation,
          retail_rate: retailRate,
          job_id: jobId,
          metal_type: metalType,
          alloy: alloy,
          specifics: specifics,
          location: location,
          description: description,
          unit_cost: unitCost
        };
      } else {
        lineAllocationsData[lineId] = {
          total_received: 0,
          job_allocation: 0,
          stock_allocation: 0,
          retail_rate: 20 
        };
      }
    });

    return lineAllocationsData;
  }

  // Store all line IDs initially present
  const allLineIds = new Set();
  document
    .querySelectorAll(
      "#pendingItems tr[data-line-id], #receivedItems tr[data-line-id]",
    )
    .forEach((row) => {
      allLineIds.add(row.dataset.lineId);
    });

  // Form submission
  document
    .getElementById("saveChanges")
    .addEventListener("click", async function (event) {
      event.preventDefault(); // Prevent default form submission

      // Clear previous validation states potentially set by backend errors
      document
        .querySelectorAll(".is-invalid")
        .forEach((el) => el.classList.remove("is-invalid"));

      // Usar a nova função para coletar dados simplificados
      const lineAllocationsData = collectDeliveryData();

      // Basic check if any allocation data was generated
      if (Object.keys(lineAllocationsData).length === 0) {
        console.warn("No allocation data found to submit.");
        return;
      }

      // Proceed with submission - Backend will handle validation
      const form = document.getElementById("deliveryReceiptForm");
      const csrfToken = document.querySelector(
        "input[name=csrfmiddlewaretoken]",
      ).value;
      const hiddenInput = form.querySelector("#receivedQuantities"); // Find the original input

      // Ensure the hidden input exists before modifying
      if (hiddenInput) {
        hiddenInput.value = JSON.stringify(lineAllocationsData);
      } else {
        console.error("Hidden input field '#receivedQuantities' not found!");
        alert("Error preparing form data. Cannot save."); // Inform user
        return;
      }

      // Disable save button during submission
      event.target.disabled = true;
      event.target.innerHTML =
        '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';

      try {
        // Use the current URL as the action if form.action is not set
        const formAction = form.action || window.location.href;
        console.log("Sending data:", {
          fieldName: hiddenInput.name,
          value: hiddenInput.value
        });
        const response = await fetch(formAction, {
          method: "POST",
          body: new FormData(form),
          headers: {
            "X-CSRFToken": csrfToken, // Use the retrieved token
          },
        });

        if (response.ok) {
          window.location.href = "/purchases/delivery-receipts/";
        } else {
          const data = await response.json();
          alert(
            data.error ||
            "An error occurred while saving the delivery receipt.",
          );
        }
      } catch (error) {
        console.error("Error:", error);
        alert("An error occurred while saving the delivery receipt.");
      }
    });
});
