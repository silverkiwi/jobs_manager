/**
 * Purchase Order Summary Management
 * 
 * Handles updating the job summary section
 */

import { getState } from "./purchase_order_state.js";
import { updateJobsList } from "./job_section.js";
import { updateSummarySection } from "./summary.js";

/**
 * Updates the job summary section with details about each job's materials costs
 */
export function updateJobSummary() {
  const state = getState();
  if (!state.grid || !state.grid.api) {
    console.error("Grid instance not found.");
    return;
  }

  // Create a map to track job totals
  const jobTotals = new Map();

  // Iterate through grid rows to calculate summary data
  state.grid.api.forEachNode((node) => {
    const jobId = node?.data?.job;
    if (!jobId) return;

    const job = state.purchaseData.jobs.find((j) => j.id === jobId);
    if (!job) return;

    // Calculate cost for this line item
    const quantity = node.data.quantity || 0;
    const unitCost =
      node.data.price_tbc || node.data.unit_cost === null
        ? 0
        : node.data.unit_cost || 0;
    const lineCost = quantity * unitCost;

    // Add to job total
    if (!jobTotals.has(jobId)) {
      jobTotals.set(jobId, {
        id: jobId,
        job_number: job.job_number,
        name: job.name,
        client_name: job.client_name,
        estimated_materials: job.estimated_materials,
        materials_purchased: 0,
      });
    }

    jobTotals.get(jobId).materials_purchased += lineCost;
  });

  // Convert map to array and sort by job number
  const jobSummaries = Array.from(jobTotals.values()).sort((a, b) => {
    // Convert both job numbers to strings and compare
    const aNum = String(a.job_number || "");
    const bNum = String(b.job_number || "");
    return aNum.localeCompare(bNum);
  });

  // Update the job cards and summary section
  updateJobsList(jobSummaries);
  updateSummarySection();
}
