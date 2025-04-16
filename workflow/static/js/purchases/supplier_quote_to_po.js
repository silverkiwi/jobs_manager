udocument.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('quoteUploadForm');
    const fileInput = document.getElementById('quoteFile');
    const uploadButton = document.querySelector('#quoteUploadForm button');
    
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
    
    // Function to process the quote file
    function processQuoteFile(formData) {
        // Show loading indicator
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'alert alert-info';
        loadingIndicator.textContent = 'Processing quote...';
        loadingIndicator.id = 'loadingIndicator';
        document.querySelector('.container-fluid').appendChild(loadingIndicator);
        
        // Submit the form
        fetch('/api/extract-supplier-quote/', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading indicator
            document.getElementById('loadingIndicator').remove();
            
            if (data.success) {
                // Redirect to the new PO form with the extracted data
                window.location.href = '/purchases/purchase-orders/new/?quote_data=' + encodeURIComponent(JSON.stringify(data.data));
            } else {
                alert(data.error || 'An error occurred while processing the quote.');
            }
        })
        .catch(error => {
            // Remove loading indicator
            if (document.getElementById('loadingIndicator')) {
                document.getElementById('loadingIndicator').remove();
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