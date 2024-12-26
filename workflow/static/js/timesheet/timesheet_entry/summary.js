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

    // Sum all the hours in the grid
    grid.forEachNode(node => {
        if (node?.data?.hours > 0) {
            totalHours += node.data.hours;
        }
    });

    // Update the summary section dynamically
    const actualHoursElement = document.querySelector(".summary-section .actual-hours");
    const scheduledHours = window.timesheet_data.staff.scheduled_hours;

    // If the actualHoursElement doesn't exist, create it
    if (!actualHoursElement) {
        const summarySection = document.querySelector(".summary-section");
        const newElement = document.createElement("p");
        newElement.className = "lead actual-hours";
        summarySection.appendChild(newElement);
    }

    const actualHoursElementFinal = document.querySelector(".summary-section .actual-hours");
    actualHoursElementFinal.innerHTML = `<strong>Actual Hours: ${totalHours.toFixed(2)}</strong>`;

    // Check for inconsistency
    if (totalHours > scheduledHours) {
        actualHoursElementFinal.className = ("alert alert-danger actual-hours");
        renderMessages([{ level: "warning", message: "Total hours exceed scheduled hours!" }]);
    } else {
        actualHoursElementFinal.className = ("lead actual-hours");
    }
}