// deserialize_timesheet.js
document.addEventListener('DOMContentLoaded', function() {
    const timesheetElement = document.getElementById('timesheetData');
    if (timesheetElement) {
        try {
            const rawData = JSON.parse(timesheetElement.textContent);
            window.timesheet_data = {
                ...rawData,
                time_entries: loadExistingTimeEntries(rawData.time_entries)
            };
            console.log('Debug: Loaded timesheet data:', window.timesheet_data);
        } catch (error) {
            console.error('Failed to parse timesheet data:', error);
        }
    } else {
        console.error('Could not find timesheet data element.');
    }
});

function loadExistingTimeEntries(entries) {
    return entries.map(entry => ({
        job_number: entry.job_pricing.related_job.job_number,
        job_name: entry.job_pricing.related_job.name,
        customer: entry.job_pricing.related_job.client?.name || 'Shop Job',
        description: entry.description,
        rate_type: getRateTypeFromMultiplier(entry.rate_multiplier),
        hours: entry.minutes / 60,
        wage_amount: entry.cost,
        bill_amount: entry.revenue,
        is_billable: entry.is_billable,
        notes: entry.note,
        charge_out_rate: entry.charge_out_rate
    }));
}

function getRateTypeFromMultiplier(multiplier) {
    switch (multiplier) {
        case 1.5: return '1.5';
        case 2.0: return '2.0';
        default: return 'Ord';
    }
}