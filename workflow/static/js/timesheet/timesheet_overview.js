import { initializeWeekPicker } from "./week_picker.js";
import { initializePaidAbsenceModal } from "./paid_absence_modal.js";

document.addEventListener("DOMContentLoaded", () => {
  console.log("Initializing...");
  initializeWeekPicker("weekPickerModal", "/timesheets/overview/{start_date}/");
  initializePaidAbsenceModal("paidAbsenceModal", window.location.href);
});
