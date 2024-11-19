document.addEventListener('DOMContentLoaded', function () {
    try {
        // Fetch JSON from <script> tags
        const jobsDataElement = document.getElementById('jobs-data');
        const timesheetEntriesDataElement = document.getElementById('timesheet-entries-data');

        if (!jobsDataElement || !timesheetEntriesDataElement) {
            throw new Error('Required data elements are missing from the DOM.');
        }

        // Parse JSON
        const jobs = JSON.parse(jobsDataElement.textContent);
        const timesheetEntries = JSON.parse(timesheetEntriesDataElement.textContent);

        console.log('Deserialized Jobs:', jobs);
        console.log('Deserialized Timesheet Entries:', timesheetEntries);

        // Transform timesheet entries (if needed)
        const transformedEntries = timesheetEntries.map(entry => ({
            ...entry,
            rate_type: getRateTypeFromMultiplier(entry.rate_multiplier),
        }));

        // Expose to global scope (if needed)
        window.jobs = jobs;
        window.transformedTimesheetEntries = transformedEntries;

        console.log('Transformed Timesheet Entries:', transformedEntries);
    } catch (error) {
        console.error('Error during deserialization or transformation:', error);
    }
});

function getRateTypeFromMultiplier(multiplier) {
    switch (multiplier) {
        case 1.5: return '1.5';
        case 2.0: return '2.0';
        default: return 'Ord';
    }
}
