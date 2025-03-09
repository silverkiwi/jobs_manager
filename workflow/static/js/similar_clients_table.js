function initializeSimilarClientsTable() {
    const form = document.getElementById('client-form');
    const nameInput = document.querySelector('input[name="name"]');
    const emailInput = document.querySelector('input[name="email"]');
    const phoneInput = document.querySelector('input[name="phone"]');
    const addressInput = document.querySelector('input[name="address"]');
    const accountCustomerInput = document.querySelector('input[name="is_account_customer"]');
    const xeroContactIdInput = document.querySelector('input[name="xero_contact_id"]');
    const rawJsonInput = document.querySelector('input[name="raw_json"]');
    const submitButton = form.querySelector('button[type="submit"]');
    const similarClientsDiv = document.getElementById('similar-clients');
    const similarClientsList = document.getElementById('similar-clients-list');
    let searchTimeout;
    
    // Store selectedClientId on window scope so other scripts can access it
    window.selectedClientId = null;

    // Function to search for similar clients
    function searchSimilarClients(query) {
        if (query && query.length >= 3) {
            fetch(`/api/client-search/?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    similarClientsList.innerHTML = '';
                    
                    if (data.results.length > 0) {
                        data.results.forEach(client => {
                            const row = document.createElement('tr');
                            row.setAttribute('data-client-id', client.id);
                            row.style.cursor = 'pointer';
                            row.innerHTML = `
                                <td>${client.name}</td>
                                <td>${client.email}</td>
                                <td>${client.phone}</td>
                                <td>${client.address}</td>
                                <td>${client.last_invoice_date}</td>
                                <td>${client.total_spend}</td>
                            `;
                            row.addEventListener('click', () => selectClient(client));
                            similarClientsList.appendChild(row);
                        });
                        similarClientsDiv.style.display = 'block';
                    } else {
                        similarClientsDiv.style.display = 'none';
                    }
                })
                .catch(error => {
                    console.error('Error searching clients:', error);
                    similarClientsDiv.style.display = 'none';
                });
        } else {
            similarClientsDiv.style.display = 'none';
        }
    }

    // Function to update form with client data
    function selectClient(client) {
        console.log('Client selected:', client);
        nameInput.value = client.name;
        emailInput.value = client.email;
        phoneInput.value = client.phone;
        addressInput.value = client.address;
        accountCustomerInput.checked = client.is_account_customer;
        
        // Set Xero Contact ID field
        if (xeroContactIdInput && client.xero_contact_id) {
            xeroContactIdInput.value = client.xero_contact_id;
        }
        
        // Set raw_json field directly from client data
        if (rawJsonInput && client.raw_json) {
            rawJsonInput.value = JSON.stringify(client.raw_json);
        }
        
        // Update the window-scoped selectedClientId
        window.selectedClientId = client.id;
        console.log('Set selectedClientId to:', window.selectedClientId);
        submitButton.textContent = 'Select Client';
        
        // Add selected class to the clicked row and remove from others
        const rows = similarClientsList.getElementsByTagName('tr');
        for (let row of rows) {
            row.classList.remove('table-primary');
        }
        const selectedRow = document.querySelector(`tr[data-client-id="${client.id}"]`);
        if (selectedRow) {
            selectedRow.classList.add('table-primary');
        }
    }

    // Handle form submission
    form.addEventListener('submit', function(e) {
        if (window.selectedClientId) {
            console.log('Form submitted with selectedClientId:', window.selectedClientId);
            e.preventDefault();
            try {
                // Attempt to post message to opener
                if (window.opener) {
                    // Get the xero contact ID
                    const xeroId = xeroContactIdInput ? xeroContactIdInput.value : '';
                    console.log('Sending Xero Contact ID:', xeroId);
                    
                    window.opener.postMessage({
                        type: 'CLIENT_SELECTED',
                        clientId: window.selectedClientId,
                        clientName: nameInput.value,
                        xeroContactId: xeroId
                    }, '*');
                } else {
                    console.error('No window.opener found');
                }
                
                // Close the window after sending the message
                console.log('Closing window');
                window.close();
            } catch (error) {
                console.error('Error in form submission handler:', error);
            }
        } else {
            console.log('Form submitted without selectedClientId - proceeding with normal submission');
        }
    });

    // Handle input changes
    nameInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        window.selectedClientId = null;
        submitButton.textContent = 'Add Client';
        
        // Clear Xero Contact ID when client name is changed
        if (xeroContactIdInput) {
            xeroContactIdInput.value = '';
        }
        
        // Clear raw_json when client name is changed
        if (rawJsonInput) {
            rawJsonInput.value = '';
        }
        
        // Add delay to prevent too many requests
        searchTimeout = setTimeout(() => {
            searchSimilarClients(query);
        }, 300); // 300ms delay
    });

    // Check for initial name value and search if present
    const initialName = nameInput.value.trim();
    if (initialName) {
        searchSimilarClients(initialName);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeSimilarClientsTable);