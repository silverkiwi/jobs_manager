$(document).ready(function () {
    function loadOverviewData(startDate) {
        let url = startDate ? `/timesheets/overview/${startDate}/` : `/timesheets/overview/`;

        $.ajax({
            url: url,
            method: 'GET',
            data: {
                'ajax': true
            },
            success: function (response) {
                const rawData = response.raw_data;
                renderDaysChart(rawData);
                renderStaffChart(rawData);
                renderJobChart(rawData);
            },
            error: function () {
                alert('Error fetching data for the timesheet overview.');
            }
        });
    }

    function renderDaysChart(data) {
        const dayLabels = [...new Set(data.map(entry => entry.date))];
        const totalHours = dayLabels.map(day => data.filter(entry => entry.date === day).reduce((sum, entry) => sum + entry.hours_worked, 0));

        Highcharts.chart('days-chart', {
            chart: {
                type: 'column'
            },
            title: {
                text: 'Total Hours Worked Per Day'
            },
            xAxis: {
                categories: dayLabels
            },
            yAxis: {
                min: 0,
                title: {
                    text: 'Hours Worked'
                }
            },
            series: [{
                name: 'Hours Worked',
                data: totalHours
            }]
        });
    }

    function renderStaffChart(data) {
        const staffData = {};

        data.forEach(entry => {
            if (!staffData[entry.staff_member]) {
                staffData[entry.staff_member] = { totalHours: 0, shopHours: 0 };
            }
            staffData[entry.staff_member].totalHours += entry.hours_worked;
            if (entry.job_type === 'OVERHEAD') {
                staffData[entry.staff_member].shopHours += entry.hours_worked;
            }
        });

        const staffNames = Object.keys(staffData);
        const totalHours = staffNames.map(name => staffData[name].totalHours);
        const shopHours = staffNames.map(name => staffData[name].shopHours);

        Highcharts.chart('staff-chart', {
            chart: {
                type: 'bar'
            },
            title: {
                text: 'Total Hours Worked by Staff'
            },
            xAxis: {
                categories: staffNames
            },
            yAxis: {
                min: 0,
                title: {
                    text: 'Hours Worked'
                }
            },
            series: [{
                name: 'Total Hours',
                data: totalHours
            }, {
                name: 'Shop Hours',
                data: shopHours
            }]
        });
    }

    function renderJobChart(data) {
        const jobData = {};

        data.forEach(entry => {
            if (!jobData[entry.job_name]) {
                jobData[entry.job_name] = { totalHours: 0, estimatedHours: entry.estimated_hours };
            }
            jobData[entry.job_name].totalHours += entry.hours_worked;
        });

        const jobNames = Object.keys(jobData);
        const totalHours = jobNames.map(name => jobData[name].totalHours);
        const hoursRemaining = jobNames.map(name => Math.max(0, jobData[name].estimatedHours - jobData[name].totalHours));

        Highcharts.chart('job-chart', {
            chart: {
                type: 'column'
            },
            title: {
                text: 'Job Progress Overview'
            },
            xAxis: {
                categories: jobNames
            },
            yAxis: {
                min: 0,
                title: {
                    text: 'Hours'
                }
            },
            series: [{
                name: 'Total Hours Spent',
                data: totalHours
            }, {
                name: 'Hours Remaining',
                data: hoursRemaining
            }]
        });
    }

    // Initial load for default or provided start date
    loadOverviewData("{{ start_date }}");
});