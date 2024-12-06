document.addEventListener("DOMContentLoaded", function () {
    const dateRanges = {
        "This month": {
            dates: [moment().startOf("month"), moment().endOf("month")],
            periodType: "month"
        },
        "Last month": {
            dates: [
                moment().subtract(1, "month").startOf("month"),
                moment().subtract(1, "month").endOf("month"),
            ],
            periodType: "month"
        },
        "This quarter": {
            dates: [moment().startOf("quarter"), moment().endOf("quarter")],
            periodType: "quarter"
        },
        "Last quarter": {
            dates: [
                moment().subtract(1, "quarter").startOf("quarter"),
                moment().subtract(1, "quarter").endOf("quarter"),
            ],
            periodType: "quarter"
        },
        "This financial year": {
            dates: [
                moment().month(3).startOf("month"),
                moment().add(1, "year").month(2).endOf("month"),
            ],
            periodType: "year"
        },
        "Last financial year": {
            dates: [
                moment().subtract(1, "year").month(3).startOf("month"),
                moment().month(2).endOf("month"),
            ],
            periodType: "year"
        },
        "Debug: Last Week Daily": {
            dates: [
                moment().subtract(1, "week").endOf("week"),  // Last Sunday
                moment().subtract(1, "week").endOf("week")   // Same day for day-by-day comparison
            ],
            periodType: "day"
        }
    };

    // Populate dropdown with options
    const dropdown = document.getElementById("date-range-picker");
    Object.keys(dateRanges).forEach((rangeName, index) => {
        const option = document.createElement("option");
        option.value = rangeName;
        option.textContent = rangeName;

        if (rangeName === "Last month") {
            option.selected = true;
        }

        dropdown.appendChild(option);
    });

    // Set up compare periods input
    const compareContainer = document.getElementById("compare-container");
    compareContainer.innerHTML = `
        <label for="compare">Compare Periods:</label>
        <input type="number" id="compare" min="0" max="12" class="border p-2 w-20" value="1">
    `;

    function setDefaultComparisonPeriods(dateRangeName) {
        const compareInput = document.getElementById("compare");
        if (dateRangeName === "Debug: Last Week Daily") {
            compareInput.value = "6";  // For daily comparison, default to last 6 days
        } else if (dateRangeName.includes("month")) {
            compareInput.value = "2";  // For monthly ranges, default to 2 periods
        } else if (dateRangeName.includes("quarter")) {
            compareInput.value = "3";  // For quarterly, default to 3 periods
        } else if (dateRangeName.includes("financial year")) {
            compareInput.value = "1";  // For yearly, default to 1 period
        }
    }

    // Update date picker on selection
    dropdown.addEventListener("change", function () {
        const selectedRange = dateRanges[this.value];
        if (selectedRange) {
            const startDate = selectedRange.dates[0].format("YYYY-MM-DD");
            const endDate = selectedRange.dates[1].format("YYYY-MM-DD");

            // Update hidden fields for the selected range
            document.getElementById("start_date").value = startDate;
            document.getElementById("end_date").value = endDate;

            // Set appropriate default comparison periods
            setDefaultComparisonPeriods(this.value);

            fetchAndRenderPNLChart();
        }
    });

    // Fetch and render the Profit & Loss chart
    function fetchAndRenderPNLChart() {
        const startDate = document.getElementById('start_date').value;
        const endDate = document.getElementById('end_date').value;
        const compare = document.getElementById('compare').value;
        const selectedRange = dateRanges[document.getElementById('date-range-picker').value];
        const periodType = selectedRange.periodType;

        if (!startDate || !endDate) {
            alert("Please select both start and end dates.");
            return;
        }

        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate,
            compare: compare,
            period_type: periodType
        });

        fetch(`/api/reports/company-profit-loss/?${params}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
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
            data: values,
            stack: 'income',
            color: Highcharts.getOptions().colors[0] // Blue-ish
        }));

        const costOfSalesData = Object.entries(data.cost_of_sales).map(([name, values]) => ({
            name,
            data: values.map(v => -v), // Negative values for costs
            stack: 'costs',
            color: Highcharts.getOptions().colors[1] // Green-ish
        }));

        const expenseData = Object.entries(data.expenses).map(([name, values]) => ({
            name,
            data: values.map(v => -v), // Negative values for expenses
            stack: 'expenses',
            color: Highcharts.getOptions().colors[2] // Red-ish
        }));

        // Highcharts grouped column chart with improved styling
        Highcharts.chart('pnl-chart', {
            chart: {
                type: 'column',
                style: {
                    fontFamily: 'Inter, system-ui, sans-serif'
                }
            },
            title: { text: 'Profit & Loss Report' },
            xAxis: {
                categories: periods,
                labels: {
                    style: {
                        fontSize: '12px'
                    }
                }
            },
            yAxis: {
                title: { text: 'Amount ($)' },
                labels: {
                    formatter: function() {
                        return new Intl.NumberFormat('en-NZ', {
                            style: 'currency',
                            currency: 'NZD',
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0
                        }).format(this.value);
                    }
                }
            },
            tooltip: {
                shared: true,
                formatter: function() {
                    let tooltip = '<b>' + this.x + '</b><br/>';
                    this.points.forEach(point => {
                        tooltip += point.series.name + ': ' +
                            new Intl.NumberFormat('en-NZ', {
                                style: 'currency',
                                currency: 'NZD'
                            }).format(Math.abs(point.y)) + '<br/>';
                    });
                    return tooltip;
                }
            },
            plotOptions: {
                column: {
                    stacking: 'normal',
                    grouping: false
                }
            },
            series: [
                ...incomeData,
                ...costOfSalesData,
                ...expenseData,
                {
                    name: 'Gross Profit',
                    data: data.totals.gross_profit,
                    type: 'line',
                    color: '#000000',
                    lineWidth: 2,
                    marker: {
                        lineWidth: 2,
                        lineColor: '#000000',
                        fillColor: '#ffffff'
                    }
                }
            ]
        });
    }

    // Set initial range and trigger first load
    const initialRange = dateRanges["Last month"];
    document.getElementById("start_date").value = initialRange.dates[0].format("YYYY-MM-DD");
    document.getElementById("end_date").value = initialRange.dates[1].format("YYYY-MM-DD");
    setDefaultComparisonPeriods("Last month");

    // Event listener for the update button
    document.getElementById('update-chart').addEventListener('click', fetchAndRenderPNLChart);

    // Initial data load
    fetchAndRenderPNLChart();
});