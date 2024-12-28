import { getCurrentDateFromURL } from './utils.js'
import { fetchJobs } from './job_section.js'
import { updateSummarySection } from './summary.js'
import { renderMessages } from './messages.js';


export function initializePaidAbsenceHandlers() {
    /**
     * Handles the click event to load the Paid Absence form in a modal.
     *
     * Purpose:
     * - Dynamically fetches and renders the Paid Absence form via AJAX.
     * - Ensures the modal is populated with the correct form content.
     * - Provides feedback to the user on errors during form loading.
     *
     * Workflow:
     * 1. Prevents the default behavior of the click event.
     * 2. Sends an AJAX POST request to the current page's URL with the action `load_paid_absence`.
     * 3. On success:
     *    - Injects the returned form HTML into the modal's body.
     *    - Displays the modal to the user.
     * 4. On error:
     *    - Logs detailed error information to the console.
     *    - Alerts the user of the issue.
     *
     * Dependencies:
     * - jQuery for AJAX handling and DOM manipulation.
     * - Bootstrap for modal functionality.
     * - Server-side handling of the `load_paid_absence` action.
     */
    $('#open-paid-absence-modal').on('click', function (e) {
        e.preventDefault();

        console.log('Loading Paid Absence form...');

        $.ajax({
            url: window.location.pathname,
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: {
                action: 'load_paid_absence'
            },
            success: function (response) {
                console.log('Sucess: ', response);
                $('#paidAbsenceModal .modal-body').html(response.form_html);
                $('#paidAbsenceModal').modal('show');
            },
            error: function (xhr, status, error) {
                console.error('Error:', {
                    status: status,
                    error: error,
                    response: xhr.responseText
                });
                alert('Error loading form. Please check console for details.');
            }
        })
    });

    /**
     * Handles the submission of the Paid Absence form.
     *
     * Purpose:
     * - Submits the form data for creating paid absence entries via AJAX.
     * - Updates the timesheet grid with the new entries upon success.
     * - Displays error messages for issues during the submission process.
     *
     * Workflow:
     * 1. Prevents the default form submission behavior.
     * 2. Serializes the form data for transmission.
     * 3. Sends an AJAX POST request to the current page's URL with the form data.
     * 4. On success:
     *    - Hides the modal and displays success messages.
     *    - Filters the returned entries to match the current page's date.
     *    - Updates the grid with matching entries.
     * 5. On error:
     *    - Logs detailed error information to the console.
     *    - Displays error messages to the user.
     *
     * Dependencies:
     * - jQuery for AJAX handling and DOM manipulation.
     * - `getCurrentDateFromURL` for filtering entries based on the current page's date.
     * - Server-side handling of the `add_paid_absence` action.
     * - Bootstrap for modal management.
     */
    $('#paidAbsenceModal').on('submit', '#paid-absence-form', function (e) {
        e.preventDefault();
        const form = $(this).serialize();

        console.log('Submitting Paid Absence form...');

        $.ajax({
            url: window.location.pathname,
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: form,
            success: function (response) {
                if (response.success) {
                    console.log("Success: ", response.success);
                    $('#paidAbsenceModal').modal('hide');
                    renderMessages(response.messages);

                    const currentDate = getCurrentDateFromURL();
                    console.log("Current page date:", currentDate);

                    response.entries.forEach(entry => {
                        if (entry.timesheet_date === currentDate) {
                            console.log("Adding entry to grid:", entry);
                            window.grid.applyTransaction({ add: [entry] });
                        }
                    });

                    fetchJobs();
                    updateSummarySection();
                }
            },
            error: function (xhr, status, error) {
                console.error('Error:', {
                    status: status,
                    error: error,
                    response: xhr.responseText
                });
                renderMessages([{ level: 'error', message: 'Error adding paid absences.' }]);
            }
        });
    });
}