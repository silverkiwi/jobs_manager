document.addEventListener("DOMContentLoaded", function () {
    const dateRanges = {
        "This month": [moment().startOf("month"), moment().endOf("month")],
        "Last month": [
            moment().subtract(1, "month").startOf("month"),
            moment().subtract(1, "month").endOf("month"),
        ],
        "This quarter": [moment().startOf("quarter"), moment().endOf("quarter")],
        "Last quarter": [
            moment().subtract(1, "quarter").startOf("quarter"),
            moment().subtract(1, "quarter").endOf("quarter"),
        ],
        "This financial year": [
            moment().month(3).startOf("month"),
            moment().add(1, "year").month(2).endOf("month"),
        ],
        "Last financial year": [
            moment().subtract(1, "year").month(3).startOf("month"),
            moment().subtract(1, "year").month(2).endOf("month"),
        ],
    };

    // Populate dropdown with options
    const dropdown = document.getElementById("date-range-picker");
    Object.keys(dateRanges).forEach((rangeName, index) => {
        const option = document.createElement("option");
        option.value = rangeName;
        option.textContent = rangeName;

        // Set "Last month" as the default selection
        if (rangeName === "Last month") {
            option.selected = true;
        }

        dropdown.appendChild(option);
    });

    // Set initial range for "Last month"
    const defaultRange = dateRanges["Last month"];
    document.getElementById("start_date").value = defaultRange[0].format("YYYY-MM-DD");
    document.getElementById("end_date").value = defaultRange[1].format("YYYY-MM-DD");

    // Update date picker on selection
    dropdown.addEventListener("change", function () {
        const selectedRange = dateRanges[this.value];
        if (selectedRange) {
            const startDate = selectedRange[0].format("YYYY-MM-DD");
            const endDate = selectedRange[1].format("YYYY-MM-DD");

            // Update hidden fields for the selected range
            document.getElementById("start_date").value = startDate;
            document.getElementById("end_date").value = endDate;

            console.log(`Selected Range: ${startDate} to ${endDate}`);
        }
    });
});

// Fetch and render the Profit & Loss chart
function fetchAndRenderPNLChart() {
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;
    const compare = document.getElementById('compare').value;

    if (!startDate || !endDate) {
        alert("Please select both start and end dates.");
        return;
    }

    // Fetch data from API
    fetch(`/api/company-profit-loss/?start_date=${startDate}&end_date=${endDate}&compare=${compare}`)
        .then(response => response.json())
        .then(data => {
            renderPNLChart(data);
        })
        .catch(error => {
            console.error('Error fetching P&L data:', error);
            alert('Failed to load report data.');
        });
}

// Render the Highcharts chart
function renderPNLChart(data) {
    const periods = data.periods;

    // Process data for charting
    const incomeData = Object.entries(data.income).map(([name, values]) => ({
        name,
        data: values
    }));

    const costOfSalesData = Object.entries(data.cost_of_sales).map(([name, values]) => ({
        name,
        data: values
    }));

    const expenseData = Object.entries(data.expenses).map(([name, values]) => ({
        name,
        data: values
    }));

    // Highcharts grouped column chart
    Highcharts.chart('pnl-chart', {
        chart: { type: 'column' },
        title: { text: 'Profit & Loss Report' },
        xAxis: { categories: periods },
        yAxis: { title: { text: 'Amount ($)' } },
        series: [
            ...incomeData,
            ...costOfSalesData,
            ...expenseData,
            {
                name: 'Gross Profit',
                data: data.totals.gross_profit,
                type: 'line'
            }
        ]
    });
}

// Event listener for the update button
document.getElementById('update-chart').addEventListener('click', fetchAndRenderPNLChart);
