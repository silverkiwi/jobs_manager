document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('quoteUploadForm');
    const fileInput = document.getElementById('quoteFile');
    const uploadButton = document.querySelector('#quoteUploadForm label');

    // Handle file selection
    fileInput.addEventListener('change', function(event) {
        console.log('File input change event triggered');
        if (fileInput.files.length > 0) {
            console.log('File selected:', fileInput.files[0].name, 'Size:', fileInput.files[0].size, 'Type:', fileInput.files[0].type);
            // Create a new FormData and add the file explicitly
            const formData = new FormData();
            formData.append('quote_file', fileInput.files[0]);
            
            // Add CSRF token explicitly
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            formData.append('csrfmiddlewaretoken', csrfToken);
            
            processQuoteFile(formData);
        } else {
            console.warn('No files selected in the change event');
        }
    });
    
    // Handle form submission
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        
        const formData = new FormData(form);
        const quoteFile = fileInput.files[0];
        
        if (!quoteFile) {
            alert('Please select a quote file.');
            return;
        }
        
        processQuoteFile(formData);
    });
    
    // Add drag and drop functionality
    uploadButton.addEventListener('dragover', function(event) {
        event.preventDefault();
        event.stopPropagation();
        uploadButton.classList.add('drag-over');
    });
    
    uploadButton.addEventListener('dragleave', function(event) {
        event.preventDefault();
        event.stopPropagation();
        uploadButton.classList.remove('drag-over');
    });
    
    uploadButton.addEventListener('drop', function(event) {
        event.preventDefault();
        event.stopPropagation();
        uploadButton.classList.remove('drag-over');
        
        if (event.dataTransfer.files.length) {
            fileInput.files = event.dataTransfer.files;
            
            // Create a new FormData and add the file
            const formData = new FormData();
            formData.append('quote_file', event.dataTransfer.files[0]);
            
            // Add CSRF token
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            formData.append('csrfmiddlewaretoken', csrfToken);

            processQuoteFile(formData);
        }
    });
    
    /**
     * Function to process the quote file
     * 
     * @param {FormData} formData 
     */
    function processQuoteFile(formData) {
        console.log('processQuoteFile called with FormData');
        
        // Show loading indicator
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'alert alert-info';
        loadingIndicator.textContent = 'Processing quote...';
        loadingIndicator.id = 'loadingIndicator';
        document.querySelector('.container-fluid').appendChild(loadingIndicator);
        
        // Submit the form
        console.log('Sending fetch request to /api/extract-supplier-quote/');
        fetch('/api/extract-supplier-quote/', {
            method: 'POST',
            body: formData,
            redirect: 'follow'
        })
        .then(response => {
            console.log('Received response:', response.status, response.statusText);
            console.log('Response headers:', [...response.headers.entries()]);
            console.log('Response redirected:', response.redirected);
            if (response.redirected) {
                console.log('Redirect URL:', response.url);
            }
            
            // Remove loading indicator
            document.getElementById('loadingIndicator').remove();
            
            if (response.redirected) {
                // If the server returned a redirect, follow it
                console.log('Following redirect to:', response.url);
                window.location.href = response.url;
            } else if (response.ok) {
                // If it's a successful JSON response, parse it
                console.log('Response OK, parsing JSON');
                return response.json().then(data => {
                    console.log('Parsed JSON data:', data);
                    if (data.success) {
                        window.location.href = '/purchases/purchase-orders/new/?quote_data=' + encodeURIComponent(JSON.stringify(data.data));
                    } else {
                        console.error('Error in response data:', data.error);
                        alert(data.error || 'An error occurred while processing the quote.');
                    }
                });
            } else {
                // Handle error responses
                console.error('Error response:', response.status);
                return response.text().then(text => {
                    console.error('Error response text:', text);
                    try {
                        const data = JSON.parse(text);
                        console.error('Parsed error data:', data);
                        alert(data.error || 'An error occurred while processing the quote.');
                    } catch (e) {
                        console.error('Failed to parse error response as JSON:', e);
                        alert('An error occurred while processing the quote.');
                    }
                }).catch(err => {
                    console.error('Failed to read error response:', err);
                    alert('An error occurred while processing the quote.');
                });
            }
        })
        .catch(error => {
            console.error('Fetch error:', error);
            
            // Remove loading indicator
            if (document.getElementById('loadingIndicator')) {
                document.getElementById('loadingIndicator').remove();
            }
            
            // Log more details about the FormData being sent
            console.error('FormData contents that caused the error:');
            try {
                for (let pair of formData.entries()) {
                    console.error(pair[0] + ':', pair[0] === 'quote_file' ?
                        `File: ${pair[1].name}, Size: ${pair[1].size}, Type: ${pair[1].type}` : pair[1]);
                }
            } catch (e) {
                console.error('Error logging FormData:', e);
            }
            
            alert('An error occurred: ' + error.message);
        });
    }
    
    // Add some basic styles for drag and drop
    const style = document.createElement('style');
    style.textContent = `
        .drag-over {
            border: 2px dashed #007bff !important;
            background-color: rgba(0, 123, 255, 0.1) !important;
        }
    `;
    document.head.appendChild(style);
});