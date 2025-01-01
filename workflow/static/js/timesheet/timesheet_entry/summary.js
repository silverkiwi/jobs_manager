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
    const shopEntriesLog = []; // Array to log shop entries

    console.log('--- Starting Summary Section Update ---');

    // Sum all the hours in the grid
    grid.forEachNode(node => {
        console.log('Processing Node:', {
            id: node?.data?.id,
            hours: node?.data?.hours,
            jobName: node?.data?.job_data?.name,
            clientName: node?.data?.job_data?.client_name
        });

        const jobData = node?.data?.job_data;
        const hours = node?.data?.hours || 0;

        if (hours > 0) {
            totalHours += hours;
            console.log(`Added ${hours} to total hours. New total: ${totalHours}`);

            node.data.is_billable ? billableCount++ : nonBillableCount++;
        }

        if (jobData && jobData.client_name === 'MSM (Shop)') {
            const previousShopHours = shopHours;
            shopHours += hours;
            shopEntriesLog.push({
                jobName: jobData.name,
                hours: hours,
                previousTotal: previousShopHours,
                newTotal: shopHours
            });
            console.log('Shop Entry Found:', {
                jobName: jobData.name,
                hours: hours,
                previousShopHoursTotal: previousShopHours,
                newShopHoursTotal: shopHours
            });
        }

        if (node?.data?.inconsistent) {
            hasInconsistencies = true;
        }

        if (jobData && jobData.hours_spent >= jobData.estimated_hours) {
            jobsWithIssues.push(jobData.name ? jobData.name : 'No Job Name');
        }
    });

    console.log('--- Summary Calculation Results ---', {
        totalHours,
        shopHours,
        billableCount,
        nonBillableCount,
        shopEntriesDetail: shopEntriesLog,
        hasInconsistencies,
        jobsWithIssues
    });

    // Update the summary table dynamically
    const scheduledHours = Number(window.timesheet_data.staff.scheduled_hours).toFixed(1);

    const summaryTableBody = document.getElementById('summary-table-body');
    if (!summaryTableBody) {
        console.error('Summary table not found');
        return;
    }

    // Log final calculations before rendering
    console.log('Final calculations for display:', {
        totalHoursDisplay: totalHours.toFixed(1),
        scheduledHours: scheduledHours,
        shopHoursDisplay: shopHours.toFixed(1),
        shopHoursPercentage: shopHours > 0 ? ((shopHours / totalHours) * 100).toFixed(1) : 0
    });

    summaryTableBody.innerHTML = `
        <tr class="${totalHours < scheduledHours ? 'table-danger' : totalHours > scheduledHours ? 'table-warning' : 'table-success'}">
            <td>Total Hours</td>
            <td>${totalHours.toFixed(1)} / ${scheduledHours}</td>
        </tr>
        <tr>
            <td>Billable Entries</td>
            <td>${billableCount > 0 ? ((billableCount / (billableCount + nonBillableCount)) * 100).toFixed(1) + '%' : 'No billable entries detected.'}</td>
        </tr>
        <tr>
            <td>Non-Billable Entries</td>
            <td>${nonBillableCount > 0 ? ((nonBillableCount / (billableCount + nonBillableCount)) * 100).toFixed(1) + '%' : 'No non-billable entries detected.'}</td>
        </tr>
        <tr>
            <td>Shop Hours</td>
            <td>${shopHours.toFixed(1)} (${shopHours > 0 ? ((shopHours / totalHours) * 100).toFixed(1) + '%' : 'No shop hours detected'})</td>
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

    console.log('--- Summary Section Update Complete ---');
}
