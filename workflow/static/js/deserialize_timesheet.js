document.addEventListener('DOMContentLoaded', function () {
    try {
        // Deserialization
        const timesheetEntries = window.timesheetEntries || [];
        const jobs = window.jobs || [];

        console.log('Deserialized Timesheet Entries:', timesheetEntries);
        console.log('Deserialized Jobs:', jobs);

        // Data Transformation (if needed)
        const transformedEntries = timesheetEntries.map(entry => ({
            ...entry,
            rate_type: getRateTypeFromMultiplier(entry.rate_multiplier),
        }));

        // Expose to global scope (if needed elsewhere)
        window.transformedTimesheetEntries = transformedEntries;
        window.jobs = jobs;

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
