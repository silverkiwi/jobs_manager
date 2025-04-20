document.addEventListener('DOMContentLoaded', function () {
    console.log('KPI Calendar script loaded and executing');
    
    let calendarEl = document.getElementById('calendar');
    let calendarLoader = document.getElementById('calendarLoader');
    
    // Check if necessary elements are found
    if (!calendarEl) {
        console.error('Calendar element not found in DOM!');
        return;
    }
    
    if (!calendarLoader) {
        console.warn('Calendar loader element not found in DOM!');
    }

    const currencyFormatter = new Intl.NumberFormat('en-NZ', {
        style: 'currency',
        currency: 'NZD'
    });

    let calendar;

    function initializeCalendar() {
        console.log('Initializing calendar');
        calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            firstDay: 1, // Start on Monday
            hiddenDays: [0, 6], // Hide Sunday (0) and Saturday (6)
            showNonCurrentDates: false,
            height: 'auto',
            headerToolbar: {
                left: 'prev,next',
                center: 'title',
                right: ''
            },
            datesSet: function (dateInfo) {
                console.log('Calendar dates changed, requesting new data');
                updateCalendarData(dateInfo.view.calendar.getDate());
            },
            eventContent: function (arg) {
                if (arg.event.display === 'background') {
                    return null; // Skip content for background events
                }

                const props = arg.event.extendedProps;
                if (!props) {
                    return null;
                }

                // Round values for cleaner display
                const billable = props.billable_hours != null ? parseFloat(props.billable_hours).toFixed(1) : '0.0';
                const totalHours = props.total_hours != null ? parseFloat(props.total_hours).toFixed(1) : '0.0';
                const shopHours = props.shop_hours != null ? parseFloat(props.shop_hours).toFixed(1) : '0.0';
                const shopPercentage = props.shop_percentage != null ? parseFloat(props.shop_percentage).toFixed(0) : '0';
                const gp = props.gross_profit != null ? currencyFormatter.format(props.gross_profit) : '$0.00';
                
                // Determine class based on status
                const colorClass = props.color ? `event-card-${props.color}` : '';

                // Create HTML with tooltip data directly in the card
                return {
                    html: `<div class="event-content ${colorClass}">
                            <div class="status-indicator status-indicator-${props.color || 'green'}"></div>
                            <div class="event-title">${billable}h</div>
                            <div class="event-gp">${gp}</div>
                            <div class="event-details">
                                <div class="event-detail-item">
                                    <span class="event-detail-value">${totalHours}h</span>
                                    <span class="event-detail-label">Total</span>
                                </div>
                                <div class="event-detail-item">
                                    <span class="event-detail-value">${shopHours}h</span>
                                    <span class="event-detail-label">Shop</span>
                                </div>
                                <div class="event-detail-item">
                                    <span class="event-detail-value">${shopPercentage}%</span>
                                    <span class="event-detail-label">Shop%</span>
                                </div>
                            </div>
                          </div>`
                };
            },
            eventDidMount: function (info) {
                if (info.event.display === 'background') {
                    return; // Do nothing for background events
                }

                const props = info.event.extendedProps;
                if (!props) {
                    return;
                }

                // Apply color class based on status
                if (props.color) {
                    info.el.classList.add(`event-${props.color}`);
                }

                // Add detailed tooltip
                const billableHours = props.billable_hours != null ? parseFloat(props.billable_hours).toFixed(1) : '0.0';
                const totalHours = props.total_hours != null ? parseFloat(props.total_hours).toFixed(1) : '0.0';
                const shopHours = props.shop_hours != null ? parseFloat(props.shop_hours).toFixed(1) : '0.0';
                const grossProfit = props.gross_profit != null ? currencyFormatter.format(props.gross_profit) : '$0.00';
                const shopPercentage = props.shop_percentage != null ? parseFloat(props.shop_percentage).toFixed(1) : '0.0';

                // Detailed tooltip
                info.el.title = `Total: ${totalHours}h | Billable: ${billableHours}h | Shop: ${shopHours}h (${shopPercentage}%) | GP: ${grossProfit}`;
            }
        });

        calendar.render();
        console.log('Calendar rendered');
    }

    function updateCalendarData(date) {
        // Show loader and hide calendar
        if (calendarLoader) calendarLoader.style.display = 'flex';
        calendarEl.style.display = 'none';
        
        const year = date.getFullYear();
        const month = date.getMonth() + 1;

        console.log(`Fetching calendar data for ${year}-${month}`);

        // Fetch updated data for the selected month
        fetch(`/api/reports/calendar?year=${year}&month=${month}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`API responded with status ${response.status}`);
                }
                return response.json().catch(err => {
                    throw new Error(`Error processing JSON response: ${err.message}`);
                });
            })
            .then(data => {
                // Debug data to console
                console.log("Calendar data received:", data);
                
                // Verify data is in expected format
                if (!data || typeof data !== 'object') {
                    throw new Error('Invalid calendar data format (empty or not an object)');
                }
                
                if (!data.calendar_data) {
                    console.warn("calendar_data not found in response", data);
                    data.calendar_data = {};
                }
                
                if (!data.monthly_totals) {
                    console.warn("monthly_totals not found in response", data);
                    data.monthly_totals = {
                        billable_hours: 0,
                        total_hours: 0,
                        shop_hours: 0,
                        gross_profit: 0,
                        days_green: 0,
                        days_amber: 0,
                        days_red: 0,
                        working_days: 0,
                        billable_percentage: 0,
                        shop_percentage: 0,
                        avg_daily_gp: 0
                    };
                }
                
                if (!data.thresholds) {
                    console.warn("thresholds not found in response", data);
                    data.thresholds = {
                        billable_threshold_green: 45,
                        billable_threshold_amber: 30,
                        daily_gp_target: 2500,
                        shop_hours_target: 20
                    };
                }
                
                try {
                    // Update calendar with new data
                    updateCalendarWithData(data);
                    
                    // Update summary cards if we have data
                    if (data.monthly_totals) {
                        updateSummaryCards(data);
                    }
                    
                    // Update captions if we have thresholds
                    if (data.thresholds) {
                        updateCaptions(data.thresholds);
                    }
                } catch (err) {
                    console.error("Error processing calendar data:", err);
                    alert(`Error processing calendar data: ${err.message}`);
                } finally {
                    // Always show calendar in the end, even with error
                    if (calendarLoader) calendarLoader.style.display = 'none';
                    calendarEl.style.display = 'block';
                    if (calendar) {
                        calendar.updateSize();
                    }
                }
            })
            .catch(error => {
                console.error('Error loading data:', error);
                alert('Error loading calendar data: ' + error.message);
                
                // Show calendar even with error to avoid loading loop
                if (calendarLoader) calendarLoader.style.display = 'none';
                calendarEl.style.display = 'block';
            });
    }

    function updateCalendarWithData(data) {
        // Clear existing events
        if (!calendar) {
            initializeCalendar();
        }
        
        calendar.removeAllEvents();
        const events = [];
        
        try {
            // Add events from new data set
            for (const [date, dayData] of Object.entries(data.calendar_data || {})) {
                if (!dayData) continue; // Skip days without data
                
                // Ensure all properties exist, using default values when necessary
                const safeData = {
                    date: date,
                    day: new Date(date).getDate(),
                    billable_hours: 0,
                    total_hours: 0,
                    shop_hours: 0,
                    shop_percentage: 0,
                    gross_profit: 0,
                    color: 'transparent',
                    ...dayData // Override defaults with actual data when available
                };
                
                // Check and fix NaN or undefined values
                for (const [key, value] of Object.entries(safeData)) {
                    if (value === null || value === undefined || (typeof value === 'number' && isNaN(value))) {
                        console.warn(`Invalid value for ${key} on date ${date}:`, value);
                        safeData[key] = 0;
                    }
                }
                
                // Add background event to color the cell (with low z-index)
                events.push({
                    start: date,
                    allDay: true,
                    display: 'background',
                    backgroundColor: getColorForStatus(safeData.color),
                    classNames: [safeData.color]
                });
                
                // Add event with data to display (with high z-index)
                events.push({
                    title: `${safeData.billable_hours.toFixed(1)}h | ${currencyFormatter.format(safeData.gross_profit)}`,
                    start: date,
                    allDay: true,
                    extendedProps: safeData,
                    classNames: ['calendar-day-event']  // Add class for styling
                });
            }
            
            calendar.addEventSource(events);
        } catch (error) {
            console.error("Error creating calendar events:", error);
        }
        
        // Always call updateSize to ensure calendar is correctly sized
        calendar.updateSize();
    }

    function getColorForStatus(status) {
        switch (status) {
            case 'green':
                return 'rgba(54, 177, 67, 0.35)';
            case 'amber':
                return 'rgba(249, 199, 79, 0.35)';
            case 'red':
                return 'rgba(247, 37, 133, 0.35)';
            default:
                return 'transparent';
        }
    }

    function updateSummaryCards(data) {
        const totals = data.monthly_totals || {};

        const billableHours = totals.billable_hours != null ? totals.billable_hours.toFixed(1) : '0.0';
        const billablePercentage = totals.billable_percentage != null ? totals.billable_percentage.toFixed(1) : '0.0';
        const grossProfit = totals.gross_profit != null ? currencyFormatter.format(totals.gross_profit) : '$0.00';
        const avgDailyGP = totals.avg_daily_gp != null ? totals.avg_daily_gp.toFixed(2) : '0.00';
        const shopPercentage = totals.shop_percentage != null ? totals.shop_percentage.toFixed(1) : '0.0';

        document.getElementById('totalBillableHours').textContent = billableHours;
        document.getElementById('billablePercentage').textContent = billablePercentage;
        document.getElementById('totalGrossProfit').textContent = grossProfit;
        document.getElementById('avgDailyGP').textContent = avgDailyGP;
        document.getElementById('shopPercentage').textContent = shopPercentage;

        const shopTarget = data.thresholds && data.thresholds.shop_hours_target != null ?
            data.thresholds.shop_hours_target.toFixed(1) : '0.0';
        document.getElementById('shopTarget').textContent = shopTarget;

        document.getElementById('greenDays').textContent = totals.days_green || 0;
        document.getElementById('amberDays').textContent = totals.days_amber || 0;
        document.getElementById('redDays').textContent = totals.days_red || 0;
        document.getElementById('workingDays').textContent = totals.working_days || 0;
    }

    function updateCaptions(thresholds) {
        if (!thresholds) return;

        const greenThreshold = thresholds.billable_threshold_green || 45;
        const amberThreshold = thresholds.billable_threshold_amber || 30;

        document.getElementById('captionGreen').textContent = `≥ ${greenThreshold}`;
        document.getElementById('captionAmberMin').textContent = amberThreshold;
        document.getElementById('captionAmberMax').textContent = (greenThreshold - 0.01).toFixed(2);
        document.getElementById('captionRed').textContent = amberThreshold;
    }

    // Explicit call to updateCalendarData at the beginning to ensure data is loaded
    try {
        console.log('Initial calendar data load triggered');
        initializeCalendar(); // Ensure calendar is initialized before loading data
        // Load data for current month
        updateCalendarData(new Date());
    } catch (error) {
        console.error("Error initializing calendar:", error);
        alert("An error occurred while initializing the calendar: " + error.message);
        
        // Show calendar even with error
        if (calendarLoader) calendarLoader.style.display = 'none';
        calendarEl.style.display = 'block';
    }

    // Add specific resize listener
    window.addEventListener('resize', function () {
        console.log('Window resized, updating calendar size');
        if (calendar) {
            calendar.updateSize();
        }
    });
});
