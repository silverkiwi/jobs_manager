import { initializeWeekPicker } from "./week_picker.js";
import { initializePaidAbsenceModal } from "./paid_absence_modal.js";

document.addEventListener("DOMContentLoaded", () => {
  console.log("Initializing...");
  initializeWeekPicker("weekPickerModal", "/timesheets/overview/{start_date}/");
  initializePaidAbsenceModal("paidAbsenceModal", window.location.href);

  const exportToIMSButton = document.getElementById("exportToIMS");
  exportToIMSButton.addEventListener("click", toggleTableToIMS);
});

async function toggleTableToIMS() {
  await fetch("/timesheets/export_to_ims/", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value,
      "action": "export_to_ims"
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
      }
      if (Environment.isDebugMode()) {
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

    const tdOvertime = document.createElement("td");
    tdOvertime.textContent = staff.total_overtime;
    tr.appendChild(tdOvertime);

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
