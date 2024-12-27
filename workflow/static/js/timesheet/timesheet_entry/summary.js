/**
 * Updates the summary section with the total hours worked and compares them with scheduled hours.
 */
export function updateSummarySection() {
    const grid = window.grid;
    if (!grid) {
        console.error("Grid instance not found.");
        return;
    }

    let totalHours = 0;
    let hasInconsistencies = false;

    // Sum all the hours in the grid
    grid.forEachNode(node => {
        if (node?.data?.hours > 0) {
            totalHours += node.data.hours;
        }
        if (node?.data?.inconsistent) {
            hasInconsistencies = true;
        }
    });

    // Update the summary section dynamically
    const actualHoursElement = document.querySelector(".summary-section .actual-hours");
    const scheduledHours = window.timesheet_data.staff.scheduled_hours;

    // If the actualHoursElement doesn't exist, create it
    if (!actualHoursElement) {
        const summarySection = document.querySelector(".summary-section");
        const newElement = document.createElement("p");
        newElement.className = "actual-hours";
        summarySection.appendChild(newElement);
    }

    const actualHoursElementFinal = document.querySelector(".summary-section .actual-hours");
    actualHoursElementFinal.innerHTML = `<strong>Actual Hours: ${totalHours.toFixed(1)}</strong>`;

    // Check for inconsistency
    if (totalHours > scheduledHours) {
        actualHoursElementFinal.className = ("alert alert-danger actual-hours");
        renderMessages([{ level: "warning", message: "Total hours exceed scheduled hours!" }]);
    } else if (totalHours < scheduledHours && totalHours !== 0) { 
        actualHoursElementFinal.className = ("alert alert-danger actual-hours");
        renderMessages([{ level: "warning", message: "Total hours do not match scheduled hours!" }]);
    } else if (totalHours === scheduledHours && !hasInconsistencies) {
        actualHoursElementFinal.className = ("alert alert-success actual-hours");
    } else {
        actualHoursElementFinal.className = ("alert alert-info actual-hours");
        if (hasInconsistencies) {
            renderMessages([{ level: "warning", message: "Some entries have inconsistencies. Please review." }]);
        }
    }
}