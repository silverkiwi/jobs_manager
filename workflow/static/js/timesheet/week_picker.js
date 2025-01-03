document.addEventListener("DOMContentLoaded", function () {
    /**
     * Generates and displays a grid of buttons for all months in the current year
     * Each button shows the month name and year, and triggers generateWeeksOfMonth when clicked
     */
    function generateMonthsOfYear() {
        const calendarContainer = document.getElementById("week-calendar");
        calendarContainer.innerHTML = "";
    
        const gridContainer = document.createElement("div");
        gridContainer.className = "row g-3";
        calendarContainer.appendChild(gridContainer);
    
        const today = new Date();
        const currentYear = today.getFullYear();
    
        for (let month = 0; month < 12; month++) {
            const columnDiv = document.createElement("div");
            columnDiv.className = "col-md-4";
    
            const monthButton = document.createElement("button");
            const monthDate = new Date(currentYear, month, 1);
            monthButton.className = "btn btn-outline-secondary w-100";
            monthButton.innerText = monthDate.toLocaleDateString("en-NZ", {
                month: "long",
                year: "numeric"
            });
    
            monthButton.addEventListener("click", function () {
                generateWeeksOfMonth(month);
            });
    
            columnDiv.appendChild(monthButton);
            gridContainer.appendChild(columnDiv);
        }
    }

    /**
     * Generates and displays buttons for each week in the selected month
     * Each button shows the date range for that week and links to the timesheet overview
     * @param {number} selectedMonth - The month to generate weeks for (0-11)
     */
    function generateWeeksOfMonth(selectedMonth) {
        const calendarContainer = document.getElementById("week-calendar");
        calendarContainer.innerHTML = "";
    
        const today = new Date();
        const year = today.getFullYear();
        const firstDayOfMonth = new Date(year, selectedMonth, 1);
        const lastDayOfMonth = new Date(year, selectedMonth + 1, 0);
    
        let currentDay = new Date(firstDayOfMonth);
        if (currentDay.getDay() !== 1) {
            currentDay.setDate(currentDay.getDate() - (currentDay.getDay() - 1));
        }
    
        while (currentDay <= lastDayOfMonth) {
            const weekStart = new Date(currentDay);
            const weekEnd = new Date(currentDay);
            weekEnd.setDate(weekStart.getDate() + 4);
    
            const weekButton = document.createElement("button");
            weekButton.className = "btn btn-outline-primary mb-2";
            weekButton.innerText = `${weekStart.toLocaleDateString("en-NZ", {
                day: "numeric",
                month: "long"
            })} - ${weekEnd.toLocaleDateString("en-NZ", {
                day: "numeric",
                month: "long"
            })}`;
    
            weekButton.addEventListener("click", function () {
                const formattedStartDate = weekStart.toISOString().split("T")[0];
                window.location.href = `/timesheets/overview/${formattedStartDate}/`;
            });
    
            calendarContainer.appendChild(weekButton);
    
            currentDay.setDate(currentDay.getDate() + 7);
        }
    
        const backButton = document.createElement("button");
        backButton.className = "btn btn-outline-secondary mt-3";
        backButton.innerText = "Back to Months";
        backButton.addEventListener("click", generateMonthsOfYear);
    
        calendarContainer.appendChild(backButton);
    }

    generateMonthsOfYear();
});
