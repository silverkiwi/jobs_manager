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
