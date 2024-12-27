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
    const jobsWithIssues = [];

    // Sum all the hours in the grid
    grid.forEachNode(node => {
        const jobData = node?.data?.job_data;
        if (node?.data?.hours > 0) {
            totalHours += node.data.hours;
        }

        if (node?.data?.inconsistent) {
            hasInconsistencies = true;
        }

        if (jobData && jobData.hours_spent >= jobData.estimated_hours) {
            jobsWithIssues.push(jobData.name);
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

    // Check for inconsistency using guard clauses
    if (totalHours > scheduledHours) {
        actualHoursElementFinal.className = "alert alert-danger actual-hours";
        renderMessages([{ level: "warning", message: "Total hours exceed scheduled hours!" }]);
        return;
    }

    if (totalHours < scheduledHours && totalHours !== 0) {
        actualHoursElementFinal.className = "alert alert-danger actual-hours"; 
        renderMessages([{ level: "warning", message: "Total hours do not match scheduled hours!" }]);
        return;
    }

    if (totalHours === scheduledHours && !hasInconsistencies) {
        actualHoursElementFinal.className = "alert alert-success actual-hours";
        return;
    }

    actualHoursElementFinal.className = "alert alert-warning actual-hours";
    if (hasInconsistencies) {
        renderMessages([{ level: "warning", message: "Some entries have inconsistencies. Please review." }]);
    } else if (jobsWithIssues.length > 0) {
        renderMessages([{ level: "warning", message: `Some jobs have met or exceeded their estimated hours: ${jobsWithIssues.join(', ')}` }]);
    }
}