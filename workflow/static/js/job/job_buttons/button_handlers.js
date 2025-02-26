// Button handlers
import { getJobIdFromUrl, toggleGrid } from "./button_utils.js";
import { showQuoteModal } from "./modal_handlers.js";
import { handleSaveEventButtonClick } from "./job_events.js";
import { createXeroDocument, deleteXeroDocument } from "./xero_handlers.js";

// External functions
import {
  copyEstimateToQuote,
  debouncedAutosave,
  handlePrintWorkshop,
} from "../edit_job_form_autosave.js";
import {
  calculateTotalCost,
  calculateTotalRevenue,
} from "../grid/grid_utils.js";

/**
 * Handles all button clicks on the page by identifying which action to trigger
 * and calling the corresponding module functions.
 *
 * @param {Event} event - The click event object
 * @returns {void}
 */
export function handleButtonClick(event) {
  console.log("Button clicked:", event.target.id);
  const buttonId = event.target.id;
  const jobId = getJobIdFromUrl();

  switch (buttonId) {
    case "copyEstimateToQuote":
      copyEstimateToQuote();
      calculateTotalCost();
      calculateTotalRevenue();
      break;

    case "quoteJobButton":
      createXeroDocument(jobId, "quote");
      break;

    case "deleteQuoteButton":
      deleteXeroDocument(jobId, "quote");
      break;

    case "invoiceJobButton":
      createXeroDocument(jobId, "invoice");
      break;

    case "deleteInvoiceButton":
      deleteXeroDocument(jobId, "invoice");
      break;

    case "printWorkshopButton":
      handlePrintWorkshop();
      break;

    case "acceptQuoteButton":
      const currentDateTimeISO = new Date().toISOString();
      document.getElementById("quote_acceptance_date_iso").value =
        currentDateTimeISO;
      console.log(`Quote acceptance date set to: ${currentDateTimeISO}`);
      debouncedAutosave();
      break;

    case "contactClientButton":
      showQuoteModal(jobId, "gmail", true);
      break;

    case "saveEventButton":
      handleSaveEventButtonClick(jobId);
      break;

    case "toggleGridButton":
      toggleGrid();

    default:
      break;
  }
}
