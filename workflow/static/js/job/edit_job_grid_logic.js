/*
 * File Overview:
 * ----------------
 * This file manages the creation and interaction of grids using AG Grid. It includes
 * functionality for dynamically initializing multiple grids (time, materials, adjustments)
 * across various sections (e.g., estimate, quote, reality), and includes a special revenue grid.
 * Later we might add cost with the revenue grid.
 *
 * Key Interactions:
 * - Autosave Integration:
 *   The autosave functionality depends on grid changes triggering an event that captures
 *   the data across all relevant grids. It is crucial that the APIs for each grid are correctly
 *   initialized and stored in `window.grids` to ensure autosave has access to the necessary data.
 *
 * - AG Grid API Storage:
 *   Each grid API is stored in `window.grids` once the grid is initialized. This is critical
 *   for autosave, `calculateTotalRevenue()`, and other inter-grid operations. The revenue grid is
 *   also included here, as it is required for proper calculation and data refresh.
 *
 * - AG Grid Version Compatibility:
 *   Ensure that changes align with AG Grid version 32.2.1. Be aware of deprecated properties
 *   and avoid using older APIs that may not be compatible with this version.
 *
 * Important Notes:
 * - The `onGridReady` function, inherited from `commonGridOptions`, is responsible for storing
 *   each grid's API in `window.grids`. Do not modify the initialization logic to exclude this step.
 * - Each grid API is crucial for the autosave mechanism. Breaking or missing the correct API
 *   initialization may lead to unexpected errors or the autosave failing silently.
 * - Maintain a consistent approach to API storage and avoid changes that bypass or duplicate
 *   API handling in `onGridReady`.
 */

// Grid column definitions
import { createTrashCanColumn } from "./grid/columns.js";

// Grid options creators
import {
  createCommonGridOptions,
  createAdvancedTimeGridOptions,
  createAdvancedMaterialsGridOptions,
  createAdvancedAdjustmentsGridOptions,
  createSimpleTimeGridOptions,
  createSimpleMaterialsGridOptions,
  createSimpleAdjustmentsGridOptions,
  createSimpleTotalsGridOptions,
} from "./grid/grid_options.js";

// Revenue and cost grid options
import {
  createRevenueGridOptions,
  createCostGridOptions,
} from "./grid/revenue_cost_options.js";

// Grid initialization and management
import {
  initializeAdvancedGrids,
  initializeSimpleGrids,
  createTotalTables,
  checkGridInitialization,
} from "./grid/grid_initialization.js";

// Grid calculations
import { calculateTotalRevenue, calculateTotalCost, checkRealityValues, checkJobAccepted, updateGridOverflowClasses } from "./grid/grid_utils.js";

// Button Handler
import { handleButtonClick } from "./job_buttons/button_handlers.js";

import { loadJobDetails } from "./job_details_loader.js";
import { toggleGrid, togglePricingType } from "./job_buttons/button_utils.js";


document.addEventListener("DOMContentLoaded", function () {
  loadJobDetails();

  const trashCanColumn = createTrashCanColumn();

  // Advanced grid creation
  const commonGridOptions = createCommonGridOptions();
  const advancedTimeGridOptions = createAdvancedTimeGridOptions(
    commonGridOptions,
    trashCanColumn,
  );
  const advancedMaterialsGridOptions = createAdvancedMaterialsGridOptions(
    commonGridOptions,
    trashCanColumn,
  );
  const advancedAdjustmentsGridOptions = createAdvancedAdjustmentsGridOptions(
    commonGridOptions,
    trashCanColumn,
  );

  // Simple grid creation
  const simpleTimeGridOptions = createSimpleTimeGridOptions(
    commonGridOptions,
    trashCanColumn,
  );
  const simpleMaterialsGridOptions = createSimpleMaterialsGridOptions(
    commonGridOptions,
    trashCanColumn,
  );
  const simpleAdjustmentsGridOptions = createSimpleAdjustmentsGridOptions(
    commonGridOptions,
    trashCanColumn,
  );

  initializeAdvancedGrids(
    commonGridOptions,
    advancedTimeGridOptions,
    advancedMaterialsGridOptions,
    advancedAdjustmentsGridOptions,
  );

  initializeSimpleGrids(
    commonGridOptions,
    simpleTimeGridOptions,
    simpleMaterialsGridOptions,
    simpleAdjustmentsGridOptions,
  );

  // Grid options for Totals table (default 4 rows, autoHeight for proper resizing)
  const revenueGridOptions = createRevenueGridOptions();
  const costGridOptions = createCostGridOptions();

  createTotalTables(revenueGridOptions, costGridOptions);

  setTimeout(checkGridInitialization, 3000);
  setTimeout(calculateTotalRevenue, 1000);
  setTimeout(calculateTotalCost, 1000);
  setTimeout(checkRealityValues, 1500);
  setTimeout(checkJobAccepted, 2000);
  setTimeout(updateGridOverflowClasses, 2500);

  const isComplexJob = document.getElementById("complex-job").textContent.toLowerCase() === 'true';
  toggleGrid(isComplexJob ? "complex" : "simple");
  
  document.body.addEventListener("click", handleButtonClick);
  document.getElementById('pricingTypeDropdown').addEventListener('change', (event) => togglePricingType(event));
  document.getElementById("job_status").addEventListener('change', checkJobAccepted);
  console.log("Checking grids before checking job accepted",window.grids);

  // --- Stock Consumption Modal Logic ---
  const consumeStockBtn = document.getElementById('consumeStockBtn');
  const consumeStockModalElement = document.getElementById('consumeStockModal');
  const consumeStockModal = consumeStockModalElement ? new bootstrap.Modal(consumeStockModalElement) : null;
  const stockItemSelect = document.getElementById('stockItemSelect');
  const quantityUsedInput = document.getElementById('quantityUsed');
  const stockItemDetailsDiv = document.getElementById('stockItemDetails');
  const stockAvailableQtySpan = document.getElementById('stockAvailableQty');
  const stockUnitCostSpan = document.getElementById('stockUnitCost');
  const confirmConsumeStockBtn = document.getElementById('confirmConsumeStockBtn');
  const consumeStockForm = document.getElementById('consumeStockForm');
  // Get job ID from the main job details section (assuming an element with id 'job-id-display' or similar exists)
  // Adjust selector if needed based on edit_job_detail_section.html
  const jobIdElement = document.getElementById('job-id-display'); // Or other element holding job ID
  const jobId = jobIdElement ? jobIdElement.dataset.jobId : null;

  if (!jobId) {
      console.error("Could not determine Job ID for stock consumption.");
  }

  if (consumeStockBtn && consumeStockModal && jobId) {
      consumeStockBtn.addEventListener('click', () => {
          // Reset modal state
          if(stockItemSelect) stockItemSelect.innerHTML = '<option value="" selected disabled>Loading available stock...</option>';
          if(quantityUsedInput) {
              quantityUsedInput.value = '';
              quantityUsedInput.disabled = true;
              quantityUsedInput.max = ''; // Clear max validation
          }
          if(stockItemDetailsDiv) stockItemDetailsDiv.style.display = 'none';
          if(confirmConsumeStockBtn) confirmConsumeStockBtn.disabled = true;
          
          fetchAvailableStock(); // Fetch stock when modal is opened
  
          consumeStockModal.show();
      });
  
      // TODO: Add event listener for stockItemSelect change
      // TODO: Add event listener for quantityUsedInput input/change
      // TODO: Add event listener for confirmConsumeStockBtn click
  
  } else {
       if (!jobId) {
            console.warn("Consume Stock button disabled: Job ID not found.");
            if(consumeStockBtn) consumeStockBtn.disabled = true;
       } else {
            console.warn("Consume Stock button or modal element not found.");
       }
  }
  
  async function fetchAvailableStock() {
      if (!jobId || !stockItemSelect) return;
      console.log("Fetching stock for job:", jobId);
      
      // --- Placeholder AJAX Call ---
      // Replace with actual fetch to a new Django endpoint
      // e.g., `/api/job/${jobId}/available-stock/`
      try {
          // Simulate network delay
          await new Promise(resolve => setTimeout(resolve, 300));
          // Mock response structure: Array of {id, description, quantity, unit_cost}
          const availableStock = [
              {id: 'stock-uuid-1', description: 'Sample Sheet A (Job A)', quantity: 5.0, unit_cost: 100.00},
              {id: 'stock-uuid-2', description: 'Sample Bar B (Stock)', quantity: 12.5, unit_cost: 25.50},
              {id: 'stock-uuid-3', description: 'Sample Offcut (Stock)', quantity: 0.8, unit_cost: 100.00},
          ];
          // --- End Placeholder ---

          stockItemSelect.innerHTML = '<option value="" selected disabled>Select an item...</option>'; // Reset/placeholder
          if (availableStock.length === 0) {
               stockItemSelect.innerHTML = '<option value="" selected disabled>No stock available for this job</option>';
               return;
          }

          availableStock.forEach(item => {
              if (item.quantity > 0) { // Only show items with quantity > 0
                   const option = document.createElement('option');
                   option.value = item.id;
                   // Store details in data attributes for easy access
                   option.dataset.quantity = item.quantity;
                   option.dataset.unitCost = item.unit_cost;
                   // Display available quantity in the option text
                   option.textContent = `${item.description} (Avail: ${item.quantity})`;
                   stockItemSelect.appendChild(option);
              }
          });
      } catch (error) {
           console.error("Error fetching available stock:", error);
           stockItemSelect.innerHTML = '<option value="" selected disabled>Error loading stock</option>';
      }
  }

   // Event listener for stock item selection change
   if (stockItemSelect) {
       stockItemSelect.addEventListener('change', function() {
           const selectedOption = this.options[this.selectedIndex];
           if (!selectedOption || !selectedOption.value) {
               // Reset if placeholder selected
               if(stockItemDetailsDiv) stockItemDetailsDiv.style.display = 'none';
               if(quantityUsedInput) {
                    quantityUsedInput.value = '';
                    quantityUsedInput.disabled = true;
                    quantityUsedInput.classList.remove('is-invalid');
               }
               if(confirmConsumeStockBtn) confirmConsumeStockBtn.disabled = true;
               return;
           }

           const availableQty = parseFloat(selectedOption.dataset.quantity || 0);
           const unitCost = parseFloat(selectedOption.dataset.unitCost || 0);

           // Display details
           if(stockAvailableQtySpan) stockAvailableQtySpan.textContent = availableQty;
           if(stockUnitCostSpan) stockUnitCostSpan.textContent = unitCost.toFixed(2);
           if(stockItemDetailsDiv) stockItemDetailsDiv.style.display = 'block';

           // Enable and validate quantity input
           if(quantityUsedInput) {
               quantityUsedInput.disabled = false;
               quantityUsedInput.value = ''; // Clear previous value
               quantityUsedInput.max = availableQty;
               quantityUsedInput.classList.remove('is-invalid'); // Clear previous error state
           }
           if(confirmConsumeStockBtn) confirmConsumeStockBtn.disabled = true; // Disable until quantity is valid
       });
   }

   // Event listener for quantity used input change
   if (quantityUsedInput) {
       quantityUsedInput.addEventListener('input', function() {
           const quantityUsed = parseFloat(this.value || 0);
           const maxQuantity = parseFloat(this.max || 0);
           let isValid = true;

           if (quantityUsed <= 0 || quantityUsed > maxQuantity) {
               this.classList.add('is-invalid');
               isValid = false;
           } else {
               this.classList.remove('is-invalid');
           }
           if(confirmConsumeStockBtn) confirmConsumeStockBtn.disabled = !isValid;
       });
   }

   // Event listener for confirm consume button click
   if (confirmConsumeStockBtn) {
       confirmConsumeStockBtn.addEventListener('click', async function() {
           const stockId = stockItemSelect ? stockItemSelect.value : null;
           const quantity = quantityUsedInput ? parseFloat(quantityUsedInput.value || 0) : 0;
           const maxQuantity = quantityUsedInput ? parseFloat(quantityUsedInput.max || 0) : 0;

           // Final validation before submit
           if (!stockId || quantity <= 0 || quantity > maxQuantity) {
                // TODO: Show more specific user feedback
                alert("Please select a valid stock item and enter a quantity less than or equal to available amount.");
                return;
           }

           this.disabled = true; // Disable button during request
           this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Consuming...';

           const consumeData = {
               job_id: jobId,
               stock_item_id: stockId,
               quantity_used: quantity
           };

           // TODO: Implement actual AJAX POST request
           console.log("Submitting consume data:", consumeData);
           // Example using fetch:
           try {
               const csrfToken = document.querySelector('input[name=csrfmiddlewaretoken]').value; // Get CSRF from main page
               const response = await fetch('/api/stock/consume/', { // TODO: Define this URL properly
                   method: 'POST',
                   headers: {
                       'Content-Type': 'application/json',
                       'X-CSRFToken': csrfToken
                   },
                   body: JSON.stringify(consumeData)
               });

               // --- Placeholder Success ---
               // await new Promise(resolve => setTimeout(resolve, 700)); // Simulate network
               // const response = { ok: true, status: 200, json: async () => ({ success: true, message: "Stock consumed successfully." }) };
               // --- End Placeholder ---

               if (response.ok) {
                   const result = await response.json();
                   console.log("Consume success:", result);
                   consumeStockModal.hide();
                   // TODO: Refresh the realityMaterialsTable AG Grid
                   // Example: window.grids?.realityMaterialsTable?.api?.applyTransaction({ add: [result.new_material_entry] }); // Assuming backend returns new entry data
                   alert(result.message || "Stock consumed successfully!"); // Replace with better notification
                   // Potentially trigger autosave or data refresh
                   if (window.triggerAutosave) {
                        window.triggerAutosave({ source: 'stockConsumption' });
                   }

               } else {
                   const errorData = await response.json();
                   console.error("Consume error:", errorData);
                   alert(`Error: ${errorData.error || 'Failed to consume stock.'}`); // Replace with better notification
               }

           } catch (error) {
               console.error("Consume fetch error:", error);
               alert("An unexpected error occurred while consuming stock."); // Replace with better notification
           } finally {
                // Re-enable button
                this.disabled = false;
                this.innerHTML = 'Consume';
           }
       });
   }
   // --- End Stock Consumption Modal Logic ---

});
