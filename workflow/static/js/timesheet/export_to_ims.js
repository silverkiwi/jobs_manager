function checkIMSButton(IMSButton) {
    if (IMSButton && 'checked' in IMSButton) {
        IMSButton.checked = true;
        if (window.DEBUG_MODE) {
            console.log("IMS button checked successfully");
        }
    } else {
        console.warn('Invalid element!');
        if (window.DEBUG_MODE) {
            console.log("Failed to check IMS button: invalid element");
        }
        return false;
    }
}

function formatDate(dateStr) {
    try {
        // Remove ordinal suffixes and clean up the string
        dateStr = dateStr
            .replace(/(st|nd|rd|th)/, '')
            .trim();

        const date = new Date(dateStr);

        // Check if date is valid
        if (isNaN(date.getTime())) {
            throw new Error('Invalid date');
        }

        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    } catch (error) {
        console.error('Error formatting date:', error);
        return null;
    }
}

export function checkQueryParam(exportToIMSButton) {
    const params = new URLSearchParams(window.location.search);
    const exportToIMSQuery = params.get('export_to_ims') === '1';
  
    if (exportToIMSQuery) {
      exportToIMSButton.click();
      checkIMSButton(exportToIMSButton);
      toggleTableToIMS();
      if (window.DEBUG_MODE) {
        console.log("Export to IMS query parameter detected, toggling table to IMS view");
      }
    }
}

export async function toggleTableToIMS() {
    const IMSButton = document.getElementById("exportToIMS");
    const dateSpan = document.getElementById("current-week-display");
    const dateText = dateSpan.textContent.trim();
    const firstDate = dateText.split("-")[0].trim();

    if (IMSButton && !IMSButton.checked) {
        const url = new URL(window.location.href);
        url.searchParams.delete("export_to_ims");

        window.history.replaceState({}, "", url);
        window.location.reload();
        return;
    }

    console.log("First date before format: ", firstDate, "| After:", formatDate(firstDate));

    await fetch("/timesheets/export_to_ims/", {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
            "action": "export_to_ims",
            "X-Date": formatDate(firstDate),
        },
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            return response.json();
        })
        .then((data) => {
            if (data.success) {
                updateOverviewTable(data);
                updateNavigationUrls(data);
                updateTableHeaderIMS(data.week_days);
                updateBillableHeader();
            }
            if (window.DEBUG_MODE) {
                console.log("Export to IMS successful:", data);
            }
        })
        .catch((error) => {
            console.error("Error during export to IMS:", error);
        });
}

function updateOverviewTable(data) {
    const table = document.getElementById("overviewTable");
    if (!table) {
        console.error("Overview Table not found.");
        return;
    }
    const tbody = table.querySelector("tbody");
    if (!tbody) {
        console.error("Table body not found.");
        return;
    }
    tbody.innerHTML = "";

    data.staff_data.forEach((staff) => {
        const tr = document.createElement("tr");

        const tdName = document.createElement("td");
        tdName.textContent = staff.name;
        tr.appendChild(tdName);

        staff.weekly_hours.forEach((dayData) => {
            const td = document.createElement("td");
            td.innerHTML = `
          <div><strong>Total:</strong> ${dayData.hours}</div>
          <div><strong>Std:</strong> ${dayData.standard_hours}</div>
          <div><strong>1.5x:</strong> ${dayData.time_and_half_hours}</div>
          <div><strong>2x:</strong> ${dayData.double_time_hours}</div>
          <div><strong>Unpaid:</strong> ${dayData.unpaid_hours}</div>
          <div><strong>OT:</strong> ${dayData.overtime}</div>
          <div><small class="text-muted">${dayData.status}</small></div>
        `;
            tr.appendChild(td);
        });

        const tdTotal = document.createElement("td");
        tdTotal.textContent = staff.total_hours;
        tr.appendChild(tdTotal);

        const tdBillable = document.createElement("td");
        tdBillable.textContent = staff.total_billable_hours;
        tr.appendChild(tdBillable);

        tbody.appendChild(tr);
    });
}

function updateNavigationUrls(data) {
    const queryParam = `export_to_ims=${1}`;
    const prevLink = document.getElementById("prevWeekLink");
    const nextLink = document.getElementById("nextWeekLink");

    if (prevLink && data.prev_week_url) {
        prevLink.href = data.prev_week_url.includes("?")
            ? `${data.prev_week_url}&${queryParam}`
            : `${data.prev_week_url}?${queryParam}`;
    }
    if (nextLink && data.next_week_url) {
        nextLink.href = data.next_week_url.includes("?")
            ? `${data.next_week_url}&${queryParam}`
            : `${data.next_week_url}?${queryParam}`;
    }
}

function updateTableHeaderIMS(weekDays) {
    const headerRow = document.querySelector("#overviewTable thead tr");
    if (!headerRow) {
        console.error("Table header not found.");
        return;
    }
    const headerCells = headerRow.querySelectorAll("th");

    weekDays.forEach((dayStr, index) => {
        const day = parseDateWithoutTimezone(dayStr);
        const dayLabel = day.toLocaleDateString("en-US", { weekday: "short" });
        if (headerCells[index + 1]) {
            headerCells[index + 1].textContent = dayLabel;
        }
    });
}

function parseDateWithoutTimezone(dateStr) {
    const parts = dateStr.split("-");
    return new Date(parts[0], parts[1] - 1, parts[2], 12);
}

function updateBillableHeader() {
    const headerRow = document.querySelector("#overviewTable thead tr");
    if (!headerRow) {
        console.error("Table header not found.");
        return;
    }
    const headerCells = headerRow.querySelectorAll("th");
    if (headerCells.length < 2) {
        console.error("Not enough header cells.");
        return;
    }
    headerCells[headerCells.length - 1].textContent = "Total Billable";
}
