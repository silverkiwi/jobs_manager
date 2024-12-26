/**
 * Manages the timesheet entry modal interactions and form submissions.
 * 
 * Modal Opening Handler:
 * @listens click on #new-timesheet-btn
 * @fires AJAX request to load the timesheet form
 * 
 * Form Submission Handler:
 * @listens submit on #timesheet-form
 * @fires AJAX request to save the timesheet entry
 * 
 * Business Logic:
 * 1. Modal Opening:
 *    - Loads the timesheet entry form via AJAX
 *    - Displays the form in a modal dialog
 *    - Handles loading errors with user feedback
 * 
 * 2. Form Submission:
 *    - Submits form data to server
 *    - Creates new grid entry with job details
 *    - Updates wage and bill amounts automatically
 *    - Handles validation messages and errors
 *    - Closes modal on successful submission
 * 
 * Dependencies:
 * - Requires jQuery and Bootstrap modal
 * - Requires ag-Grid instance as window.grid
 * - Requires calculateAmounts function
 * - Requires renderMessages function
 * 
 * Data Flow:
 * - Receives job data and entry details from server
 * - Integrates new entries into the grid
 * - Updates financial calculations
 * - Manages error and success messages
 */
export function initializeModals() {
    const modal = $('#timesheetModal');

    $('#new-timesheet-btn').on('click', function (e) {
        e.preventDefault();

        console.log('Sending AJAX request...');

        $.ajax({
            url: window.location.pathname,
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: {
                action: 'load_form'
            },
            success: function (response) {
                console.log('Success:', response);
                modal.find('.modal-body').html(response.form_html);
                modal.modal('show');
            },
            error: function (xhr, status, error) {
                console.error('Error:', {
                    status: status,
                    error: error,
                    response: xhr.responseText
                });
                alert('Error loading form. Please check console for details.');
            }
        });
    });

    modal.on('submit', '#timesheet-form', function (e) {
        e.preventDefault();
        const form = $(this);

        $.ajax({
            url: window.location.pathname,
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: form.serialize(), // form.serialize() will include the CSRF token automatically
            success: function (response) {

                if (response.messages) {
                    renderMessages(response.messages);
                }
                if (response.success) {
                    // Construct complete entry object with job data
                    const gridEntry = {
                        ...response.entry,
                        job_number: response.job.job_number,
                        job_name: response.job.name,
                        client: response.job.client_name,
                        job_data: response.job,
                        // Both lines below will be calculated by calculateAmounts()
                        wage_amount: 0,
                        bill_amount: 0
                    };

                    window.grid.applyTransaction({ add: [gridEntry] });

                    // Calculate amounts for the new row
                    const lastRowNode = window.grid.getDisplayedRowAtIndex(window.grid.getDisplayedRowCount() - 1);
                    if (lastRowNode) {
                        calculateAmounts(lastRowNode.data);
                        window.grid.refreshCells({
                            rowNodes: [lastRowNode],
                            columns: ['wage_amount', 'bill_amount']
                        });
                    }

                    modal.modal('hide');
                    fetchJobs();
                }
            },
            error: function (xhr, status, error) {
                console.error('Error:', {
                    status: status,
                    error: error,
                    response: xhr.responseText
                });

                const response = JSON.parse(xhr.responseText);
                if (response.messages) {
                    renderMessages(response.messages);
                } else {
                    renderMessages([{ level: 'error', message: 'An unexpected error occurred.' }]);
                }
            }
        });
    });
}