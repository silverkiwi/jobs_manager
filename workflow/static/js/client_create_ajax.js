/**
 * client_create_ajax.js - Client Creation AJAX Handler
 * 
 * This script handles AJAX form submission for the client add form.
 * It provides the following functionality:
 * 
 * 1. Intercepts the form submission when creating a new client
 * 2. Submits the form data via AJAX to create the client in Xero
 * 3. On success, returns the client data to the opener window
 * 4. On failure, displays error messages with detailed Xero error info
 * 5. Handles duplicate client errors by displaying appropriate error messages
 * 
 * It works alongside similar_clients_table.js, which handles selecting
 * existing clients from the search results.
 */

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('client-form');
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');
    const errorDetails = document.getElementById('error-details');
    const errorType = document.getElementById('error-type');
    const errorName = document.getElementById('error-name');
    const errorEmail = document.getElementById('error-email');
    const errorEmailContainer = document.getElementById('error-email-container');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    if (!form) return; // Exit if the form doesn't exist on this page
    
    // Function to display errors
    function displayError(message, details) {
        // Set error message
        errorMessage.textContent = message || 'An error occurred while creating the client.';
        
        // Handle detailed error information if available
        if (details) {
            errorType.textContent = `Error Type: ${details.error_type || 'Unknown'}`;
            errorName.textContent = details.name || '';
            
            if (details.email) {
                errorEmail.textContent = details.email;
                errorEmailContainer.style.display = 'inline';
            } else {
                errorEmailContainer.style.display = 'none';
            }
            
            errorDetails.style.display = 'block';
        } else {
            errorDetails.style.display = 'none';
        }
        
        // Show the error container
        errorContainer.style.display = 'block';
        
        // Scroll to the error container
        errorContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    form.addEventListener('submit', function(e) {
        // Only intercept if we're not selecting an existing client
        if (!window.selectedClientId) {
            e.preventDefault();
            
            // Hide any previous error messages
            errorContainer.style.display = 'none';
            
            // Collect form data
            const formData = new FormData(form);
            
            // Submit form via AJAX
            fetch(form.action || window.location.href, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => {
                return response.json().then(data => {
                    // Add status to the data for easier handling
                    data.status = response.status;
                    return data;
                });
            })
            .then(data => {
                if (data.success) {
                    // Successfully created client - close and return data
                    if (window.opener) {
                        console.log('Successfully created client, returning data:', {
                            clientId: data.client.id,
                            clientName: data.client.name,
                            xeroContactId: data.client.xero_contact_id
                        });
                        
                        window.opener.postMessage({
                            type: 'CLIENT_SELECTED',
                            clientId: data.client.id,
                            clientName: data.client.name,
                            xeroContactId: data.client.xero_contact_id
                        }, '*');
                    }
                    window.close();
                } else {
                    // Check if this is a duplicate client error (409 Conflict)
                    if (data.status === 409 && data.existing_client) {
                        // Show duplicate client error
                        displayError(
                            `Client "${data.existing_client.name}" already exists in Xero.`, 
                            {
                                error_type: 'DuplicateClientError',
                                name: data.existing_client.name,
                                email: ''
                            }
                        );
                    } else {
                        // Show general error message
                        displayError(data.error, data.error_details);
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                displayError('An unexpected error occurred. Please try again.');
            });
        }
        // If selectedClientId exists, the default form submission will handle it
    });
}); 