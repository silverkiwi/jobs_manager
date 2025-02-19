function getJobIdFromUrl() {
    return window.location.pathname.split('/')[2];
}

// handleButtonClick() helper functions
function showQuoteModal(jobId, provider = 'gmail', contactOnly = false) {
    if (contactOnly) {
        sendQuoteEmail(jobId, provider, true)
            .catch(error => {
                console.error('Error sending quote email:', error);
                renderMessages([{ level: 'error', message: 'Failed to send quote email.' }]);
            });
        return;
    }

    const modalHtml = `
        <div class='modal fade' id='quoteModal' tabindex='-1' role='dialog' aria-labelledby='quoteModalLabel' aria-hidden='true'>
            <div class='modal-dialog' role='document'>
                <div class='modal-content'>
                    <div class='modal-header'>
                        <h5 class='modal-title' id='quoteModalLabel'>Preview and Send Quote</h5>
                        <button type='button' class='btn-close' data-bs-dismiss='modal' aria-label='Close'></button>
                    </div>
                    <div class='modal-body'>
                        <p>The quote has been generated. Please preview it in the opened tab and confirm if you'd like to send it to the client.</p>
                        
                        <div class='alert alert-info' role='alert'>
                            <p class='mb-1'>If the quote looks correct, please download the PDF from the opened tab and click 'Send Quote'.</p>
                            <hr>
                            <p class='mb-1'>This will open your email client where you can compose your message and attach the downloaded PDF</p>
                            <hr>
                            <p class='mb-0'><b>Please ensure the PDF is properly attached before sending the email to the client.</b></p>
// url-utils.js
export function getJobIdFromUrl() {
    return window.location.pathname.split('/')[2];
}

// modal-handlers.js
export function showQuoteModal(jobId, provider = 'gmail', contactOnly = false) {
    if (contactOnly) {
        sendQuoteEmail(jobId, provider, true)
            .catch(error => {
                console.error('Error sending quote email:', error);
                renderMessages([{ level: 'error', message: 'Failed to send quote email.' }]);
            });
        return;
    }

    const modalHtml = `
        <div class='modal fade' id='quoteModal' tabindex='-1' role='dialog' aria-labelledby='quoteModalLabel' aria-hidden='true'>
            <div class='modal-dialog' role='document'>
                <div class='modal-content'>
                    <div class='modal-header'>
                        <h5 class='modal-title' id='quoteModalLabel'>Preview and Send Quote</h5>
                        <button type='button' class='btn-close' data-bs-dismiss='modal' aria-label='Close'></button>
                    </div>
                    <div class='modal-body'>
                        <p>The quote has been generated. Please preview it in the opened tab and confirm if you'd like to send it to the client.</p>
                        
                        <div class='alert alert-info' role='alert'>
                            <p class='mb-1'>If the quote looks correct, please download the PDF from the opened tab and click 'Send Quote'.</p>
                            <hr>
                            <p class='mb-1'>This will open your email client where you can compose your message and attach the downloaded PDF</p>
                        </div>

                        <div id='email-alert-container' class='alert-container'></div>
                    </div>
                    <div class='modal-footer'>
                        <button type='button' class='btn btn-secondary' data-bs-dismiss='modal'>Close</button>
                        <button id='sendQuoteEmailButton' type='button' class='btn btn-primary'>Send Quote</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const quoteModal = new bootstrap.Modal(document.getElementById('quoteModal'));
    quoteModal.show();

    const sendQuoteButton = document.getElementById('sendQuoteEmailButton');
// url-utils.js
export function getJobIdFromUrl() {
    return window.location.pathname.split('/')[2];
}

// modal-handlers.js
export function showQuoteModal(jobId, provider = 'gmail', contactOnly = false) {
    if (contactOnly) {
        sendQuoteEmail(jobId, provider, true)
            .catch(error => {
                console.error('Error sending quote email:', error);
                renderMessages([{ level: 'error', message: 'Failed to send quote email.' }]);
            });
        return;
    }

    const modalHtml = `
        <div class='modal fade' id='quoteModal' tabindex='-1' role='dialog' aria-labelledby='quoteModalLabel' aria-hidden='true'>
            <div class='modal-dialog' role='document'>
                <div class='modal-content'>
                    <div class='modal-header'>
                        <h5 class='modal-title' id='quoteModalLabel'>Preview and Send Quote</h5>
                        <button type='button' class='btn-close' data-bs-dismiss='modal' aria-label='Close'></button>
                    </div>
                    <div class='modal-body'>
                        <p>The quote has been generated. Please preview it in the opened tab and confirm if you'd like to send it to the client.</p>
                        
                        <div class='alert alert-info' role='alert'>
                            <p class='mb-1'>If the quote looks correct, please download the PDF from the opened tab and click 'Send Quote'.</p>
                            <hr>
                            <p class='mb-1'>This will open your email client where you can compose your message and attach the downloaded PDF</p>
                        </div>

                        <div id='email-alert-container' class='alert-container'></div>
                    </div>
                    <div class='modal-footer'>
                        <button type='button' class='btn btn-secondary' data-bs-dismiss='modal'>Close</button>
                        <button id='sendQuoteEmailButton' type='button' class='btn btn-primary'>Send Quote</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const quoteModal = new bootstrap.Modal(document.getElementById('quoteModal'));
    quoteModal.show();

    const sendQuoteButton = document.getElementById('sendQuoteEmailButton');
    sendQuoteButton.replaceWith(sendQuoteButton.cloneNode(true));

    document.getElementById('sendQuoteEmailButton').addEventListener('click', async () => {
        try {
            const data = await sendQuoteEmail(jobId, provider);
            if (data.success) {
                renderMessages([{ level: 'success', message: 'Email client opened successfully.' }], 'email-alert-container');
            } else {
                renderMessages([{ level: 'error', message: 'Failed to open email client.' }], 'email-alert-container');
            }
        } catch (error) {
            renderMessages([{ level: 'error', message: `Error: ${error.message}` }], 'email-alert-container');
        }
    });
}

// email-handlers.js
export async function sendQuoteEmail(jobId, provider = 'gmail', contactOnly = false) {
    try {
        const endpoint = `/api/quote/${jobId}/send-email/?contact_only=${contactOnly}`;
        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();

        if (data.success && data.mailto_url) {
            const email = data.mailto_url.match(/mailto:([^?]+)/)?.[1];
            const subject = encodeURIComponent(data.mailto_url.match(/subject=([^&]+)/)?.[1]);
            const body = encodeURIComponent(data.mailto_url.match(/body=([^&]+)/)?.[1]);

            let emailUrl = '';

            if (provider === 'gmail') {

    // Remove duplicated event listeners
    sendQuoteButton.replaceWith(sendQuoteButton.cloneNode(true));

    document.getElementById('sendQuoteEmailButton').addEventListener('click', async () => {
        try {
            const data = await sendQuoteEmail(jobId, provider);
            if (data.success) {
                renderMessages([{ level: 'success', message: 'Email client opened successfully.' }], 'email-alert-container');
            } else {
                renderMessages([{ level: 'error', message: 'Failed to open email client.' }], 'email-alert-container');
            }
        } catch (error) {
            renderMessages([{ level: 'error', message: `Error: ${error.message}` }], 'email-alert-container');
        }
    });
}

async function sendQuoteEmail(jobId, provider = 'gmail', contactOnly = false) {
    try {
        const endpoint = `/api/quote/${jobId}/send-email/?contact_only=${contactOnly}`;
        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();

        if (data.success && data.mailto_url) {
            const email = data.mailto_url.match(/mailto:([^?]+)/)?.[1];
            const subject = encodeURIComponent(data.mailto_url.match(/subject=([^&]+)/)?.[1]);
            const body = encodeURIComponent(data.mailto_url.match(/body=([^&]+)/)?.[1]);

            let emailUrl = '';

            if (provider === 'gmail') {
                emailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${email}&su=${subject}&body=${body}`;
            } else if (provider === 'outlook') {
                emailUrl = `https://outlook.office.com/mail/deeplink/compose?to=${email}&subject=${subject}&body=${body}`;
            } else {
                throw new Error('Unsupported email provider.');
            }

            window.open(emailUrl, '_blank');
        } else if (!data.success) {
            console.error('Error sending email:', data.error);
        }

        return data;
    } catch (error) {
        renderMessages([{ level: 'error', message: `Error sending email: ${error.message}` }], 'email-alert-container');
        console.error('Error sending email:', error);
        throw error;
    }
}

// Function to format the event type (e.g., 'manual_note' -> 'Manual Note')
function formatEventType(eventType) {
    return eventType
        .replaceAll('_', ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
    }).format(date);
}

function addEventToTimeline(event, jobEventsList) {
    const eventType = formatEventType(event.event_type);

    const newEventHtml = `
        <div class='timeline-item list-group-item'>
            <div class='d-flex w-100 justify-content-between'>
                <div class='timeline-date text-muted small'>${formatTimestamp(event.timestamp)}</div>
            </div>
            <div class='timeline-content'>
                <h6 class='mb-1'>${eventType}</h6>
                <p class='mb-1'>${event.description}</p>
                <small class='text-muted'>By ${event.staff}</small>
            </div>
        </div>
    `;
    jobEventsList.insertAdjacentHTML('afterbegin', newEventHtml);
}

function handleSaveEventButtonClick(jobId) {
    const eventDescriptionField = document.getElementById('eventDescription');
    const description = eventDescriptionField.value.trim();

    if (!description) {
        renderError('Please enter an event description.');
        return;
    }

    const jobEventsList = document.querySelector('.timeline.list-group');
    const noEventsMessage = jobEventsList.querySelector('.text-center.text-muted');

    fetch(`/api/job-event/${jobId}/add-event/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
        body: JSON.stringify({ description }),
    })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                renderError(data.error || 'Failed to add an event.');
                return;
            }

            if (noEventsMessage) {
                noEventsMessage.remove();
            }

            addEventToTimeline(data.event, jobEventsList);

            // Clear the input field and hide the modal
            eventDescriptionField.value = '';
            const modal = bootstrap.Modal.getInstance(document.getElementById('addJobEventModal'));
            modal.hide();
        })
        .catch(error => {
            console.error('Error adding job event:', error);
            renderError('Failed to add job event. Please try again.');
        });
}

function createXeroDocument(jobId, type) {
    console.log(`Creating Xero ${type} for job ID: ${jobId}`);

    if (!jobId) {
        console.error('Job ID is missing');
        renderMessages([{ level: 'error', message: `Job id is missing!` }]);
        return;
    }

    const endpoint = type === 'invoice'
        ? `/api/xero/create_invoice/${jobId}`
        : `/api/xero/create_quote/${jobId}`;

    console.log(`Making POST request to endpoint: ${endpoint}`);

    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
    })
        .then((response) => {
            console.log(`Received response with status: ${response.status}`);
            if (!response.ok) {
                return response.json().then((data) => {
                    console.log('Response not OK, checking for redirect:', data);
                    if (data.redirect_to_auth) {
                        console.log('Auth redirect required, preparing redirect message');
                        renderMessages(
                            [
                                {
                                    level: 'error',
                                    message: 'Your Xero session seems to have ended. Redirecting you to the Xero login in seconds.'
                                }
                            ]
                        );

                        const sectionId = type === 'invoice' ? 'workflow-section' : 'quoteTimeTable';
                        setTimeout(() => {
                            const redirectUrl = `/api/xero/authenticate/?next=${encodeURIComponent(
                                `${window.location.pathname}#${sectionId}`
                            )}`;
                            console.log(`Redirecting to: ${redirectUrl}`);
                            window.location.href = redirectUrl;
                        }, 3000);

                        return;
                    }
                    throw new Error(data.message || 'Failed to create document.');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Processing response data:', data);

            if (!data) {
                console.error('No data received from server');
                renderMessages([{ level: 'error', message: 'Your Xero session seems to have ended. Redirecting you to the Xero login in seconds.' }]);
                return;
            }

            if (!data.success) {
                console.error('Document creation failed:', data.messages);
                renderMessages(data.messages || [{ level: 'error', message: 'Failed to delete document.' }]);
                return;
            }

            console.log(`${type} created successfully with Xero ID: ${data.xero_id}`);

            const documentSummary = `
            <div class='card'>
                <div class='card-header bg-success text-white'>
                    ${type === 'invoice' ? 'Invoice' : 'Quote'} Created Successfully
                </div>
                <div class='card-body'>
                    <p><strong>Xero ID:</strong> ${data.xero_id}</p>
                    <p><strong>Client:</strong> ${data.client}</p>
                    ${data.invoice_url ? `<a href='${data.invoice_url}' target='_blank' class='btn btn-info'>Go to Xero</a>` : ''}
                    ${data.quote_url ? `<a href='${data.quote_url}' target='_blank' class='btn btn-info'>Go to Xero</a>` : ''}
                    <div class="alert alert-info mt-3">
                        <small>If the button above doesn't work, you can search for the Xero ID <strong>${data.xero_id}</strong> directly in Xero to find this document.</small>
                    </div>
                </div>
            </div>
            `;

            console.log('Updating document buttons and UI');
            handleDocumentButtons(type, data.invoice_url || data.quote_url, "POST");

            document.getElementById('alert-modal-body').innerHTML = documentSummary;
            new bootstrap.Modal(document.getElementById('alert-container')).show();
        })
        .catch(error => {
            console.error('Error creating Xero document:', error);
            renderMessages([{ level: 'error', message: `An error occurred: ${error.message}` }]);
        });
}

function handleDocumentButtons(type, online_url, method) {
    console.log(`Handling document buttons for type: ${type}, method: ${method}`);

    const documentButton = document.getElementById(type === 'invoice' ? 'invoiceJobButton' : 'quoteJobButton');
    console.log(`Document button found: ${documentButton ? 'yes' : 'no'}`);

    const statusCheckbox = document.getElementById(type === 'invoice' ? 'invoiced_checkbox' : 'quoted_checkbox');
    console.log(`Status checkbox found: ${statusCheckbox ? 'yes' : 'no'}`);

    const deleteButton = document.getElementById(type === 'invoice' ? 'deleteInvoiceButton' : 'deleteQuoteButton')
    console.log(`Delete button found: ${deleteButton ? 'yes' : 'no'}`);

    const xeroLink = document.getElementById(type === 'invoice' ? 'invoiceUrl' : 'quoteUrl');
    console.log(`Xero link found: ${xeroLink ? 'yes' : 'no'}`);

    if (online_url) {
        console.log(`Setting Xero link href to: ${online_url}`);
        xeroLink.href = online_url;
    }

    switch (method) {
        case 'POST':
            console.log('Handling POST method');
            documentButton.disabled = true;
            deleteButton.style.display = 'inline-block';

            statusCheckbox.disabled = false;
            statusCheckbox.checked = true;

            xeroLink.style.display = 'inline-block';
            break;

        case 'DELETE':
            console.log('Handling DELETE method');
            documentButton.disabled = false;
            deleteButton.style.display = 'none';

            statusCheckbox.disabled = true;
            statusCheckbox.checked = false;

            xeroLink.style.display = 'none';
    }
    console.log('Document button handling complete');
}

function deleteXeroDocument(jobId, type) {
    console.log(`Deleting Xero ${type} for job ID: ${jobId}`);

    if (!confirm(`Are you sure you want to delete this ${type}?`)) {
        console.log('User cancelled delete operation');
        return;
    }

    const endpoint = type === 'invoice'
        ? `/api/xero/delete_invoice/${jobId}`
        : `/api/xero/delete_quote/${jobId}`;

    console.log(`Making DELETE request to endpoint: ${endpoint}`);

    fetch(endpoint, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
    })
        .then((response) => {
            console.log(`Received response with status: ${response.status}`);
            if (!response.ok) {
                return response.json().then((data) => {
                    console.log('Response not OK, checking for redirect:', data);
                    if (data.redirect_to_auth) {
                        console.log('Auth redirect required, preparing redirect message');
                        const sectionId = type === 'invoice' ? 'workflow-section' : 'quoteTimeTable';
                        setTimeout(() => {
                            const redirectUrl = `/api/xero/authenticate/?next=${encodeURIComponent(
                                `${window.location.pathname}#${sectionId}`
                            )}`;
                            console.log(`Redirecting to: ${redirectUrl}`);
                            window.location.href = redirectUrl;
                        }, 3000);

                        return;
                    }
                    throw new Error(data.message || 'Failed to delete document.');
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Processing response data:', data);

            if (!data) {
                console.error('No data received from server');
                renderMessages([{ level: 'error', message: 'Your Xero session seems to have ended. Redirecting you to the Xero login in seconds.' }]);
                return;
            }

            if (!data.success) {
                renderMessages(data.messages);
                return;
            }

            console.log('Document deleted successfully, updating UI');
            handleDocumentButtons(type, null, 'DELETE');
            renderMessages(data.messages);
        })
        .catch(error => {
            console.error('Error deleting Xero document:', error);
            renderMessages([{ level: 'error', message: `An error occurred: ${error.message}` }]);
        });
}

// Not being used yet
function toggleGrid(commonGridOptions, trashCanColumn) {
    const simpleTimeGridOptions = createSimpleTimeGridOptions(commonGridOptions, trashCanColumn);

    const simpleMaterialsGridOptions = createSimpleMaterialsGridOptions(commonGridOptions, trashCanColumn);

    const simpleAdjustmentsGridOptions = createSimpleAdjustmentsGridOptions(commonGridOptions, trashCanColumn);

    const simpleTotalsGridOptions = createSimpleTotalsGridOptions(commonGridOptions, trashCanColumn);
}

export function handleButtonClick(event) {
    const buttonId = event.target.id;
    const jobId = getJobIdFromUrl();

    switch (buttonId) {
        case 'copyEstimateToQuote':
            copyEstimateToQuote();
            calculateTotalCost();
            calculateTotalRevenue();
            break;

        case 'quoteJobButton':
            createXeroDocument(jobId, 'quote');
            break;

        case 'deleteQuoteButton':
            deleteXeroDocument(jobId, 'quote');
            break;

        case 'invoiceJobButton':
            createXeroDocument(jobId, 'invoice');
            break;

        case 'deleteInvoiceButton':
            deleteXeroDocument(jobId, 'invoice');
            break;

        case 'acceptQuoteButton':
            const currentDateTimeISO = new Date().toISOString();
            document.getElementById('quote_acceptance_date_iso').value = currentDateTimeISO;
            console.log(`Quote acceptance date set to: ${currentDateTimeISO}`);
            debouncedAutosave();
            break;

        case 'contactClientButton':
            showQuoteModal(jobId, 'gmail', true);
            break;

        case 'saveEventButton':
            handleSaveEventButtonClick(jobId);
            break;

        case 'printWorkshopButton':
            handlePrintWorkshop();
            break;

        case 'toggleGridButton':
            toggleGrid();
            break;

        default:
            // Random clicks not on buttons don't count - don't even log them
            break;
    }
}
