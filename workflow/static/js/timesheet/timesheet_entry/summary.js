import { renderMessages } from './messages.js';


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
    let shopHours = 0;
    let billableCount = 0;
    let nonBillableCount = 0;
    let hasInconsistencies = false;
    const jobsWithIssues = [];

    // Sum all the hours in the grid
    grid.forEachNode(node => {
        console.log('Node:', node);
        const jobData = node?.data?.job_data;
        const hours = node?.data?.hours || 0;

        if (hours > 0) {
            totalHours += hours;

            node.data.is_billable ? billableCount++ : nonBillableCount++;
        }

        if (jobData && jobData.client_name === 'MSM (Shop)') {
            console.log(`Job: ${jobData.name} Hours: ${hours}`);
            shopHours += hours;
        }

        if (node?.data?.inconsistent) {
            hasInconsistencies = true;
        }

        if (jobData && jobData.hours_spent >= jobData.estimated_hours) {
            jobsWithIssues.push(jobData.name ? jobData.name : 'No Job Name');
        }
    });

    // Update the summary table dynamically
    const scheduledHours = Number(window.timesheet_data.staff.scheduled_hours).toFixed(1);

    const summaryTableBody = document.getElementById('summary-table-body');
    if (!summaryTableBody) {
        console.error('Summary table not found');
        return;
    }

    summaryTableBody.innerHTML = `
        <tr class="${totalHours < scheduledHours ? 'table-danger' : totalHours > scheduledHours ? 'table-warning' : 'table-success'}">
            <td>Total Hours</td>
            <td>${totalHours.toFixed(1)} / ${scheduledHours}</td>
        </tr>
        <tr>
            <td>Billable Entries</td>
            <td>${((billableCount / (billableCount + nonBillableCount)) * 100).toFixed(1)}%</td>
        </tr>
        <tr>
            <td>Non-Billable Entries</td>
            <td>${((nonBillableCount / (billableCount + nonBillableCount)) * 100).toFixed(1)}%</td>
        </tr>
        <tr>
            <td>Shop Hours</td>
            <td>${shopHours.toFixed(1)} (${((shopHours / totalHours) * 100).toFixed(1)}%)</td>
        </tr>
    `;

    if (hasInconsistencies || jobsWithIssues.length > 0) {
        summaryTableBody.innerHTML += `
            <tr class="table-warning">
                <td>Inconsistencies</td>
                <td>${hasInconsistencies ? "Yes" : "No"}</td>
            </tr>
        `;
        if (jobsWithIssues.length > 0) {
            summaryTableBody.innerHTML += `
                <tr class="table-warning">
                    <td>Jobs with Issues</td>
                    <td>${jobsWithIssues.join(", ")}</td>
                </tr>
            `;
        }
    }

    if ((shopHours / totalHours) >= 0.5) {
        renderMessages([{ level: "warning", message: "High shop time detected! More than 50% of hours are shop hours." }]);
    }
}