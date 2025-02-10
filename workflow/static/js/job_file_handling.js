document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-input');
    const dropZone = document.querySelector('.file-drop-zone');
    const fileList = document.getElementById('file-list');

    // Handle file selection
    fileInput.addEventListener('change', handleFiles);

    // Handle file deletion
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-file')) {
            const fileId = e.target.dataset.fileId;
            if (fileId) {
                console.log('Delete button clicked for file ID:', fileId);
                deleteFile(fileId);
            } else {
                console.warn('Delete button clicked but no file ID found');
            }
        }
    });

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Handle drop zone highlighting
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', handleDrop, false);

    function preventDefaults (e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        dropZone.classList.add('drag-over');
    }

    function unhighlight(e) {
        dropZone.classList.remove('drag-over');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    function handleFiles(filesOrEvent) {
        const files = filesOrEvent.target?.files || filesOrEvent;

        const formData = new FormData();
        formData.append('job_number', document.querySelector('[name="job_number"]').value);
        for(let file of files) {
            formData.append('files', file);
        }

        fetch('/api/job-files/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]').value
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if(data.status === 'success' || data.status === 'partial_success') {
                // Update file list without full page reload
                updateFileList(data.uploaded);
                if(data.errors) {
                    data.errors.forEach(error => console.warn(error));
                }
            } else {
                console.error('Upload failed:', data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }

    function deleteFile(fileId) {
        if (!confirm('Are you sure you want to delete this file?')) {
            return;
        }

        console.log(`Attempting to delete file with ID: ${fileId}`);

        fetch(`/api/job-files/${fileId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]').value
            }
        })
        .then(response => {
            if (response.ok) {
                console.log(`Successfully deleted file with ID: ${fileId}`);

                // Remove the file card from the UI
                // Using closest() to find the parent file-card element from the delete button
                const fileCard = document.querySelector(`[data-file-id="${fileId}"]`).closest('.file-card');
                if (fileCard) {
                    fileCard.remove();
                    console.log('File card removed from UI');
                } else {
                    console.log('File card not found in UI');
                }
            } else {
                console.error(`Failed to delete file with ID: ${fileId}. Status: ${response.status}`);
            }
        })
        .catch(error => {
            console.error('Error deleting file:', error);
        });
    }

    function updateFileList(newFiles) {
        if (!newFiles || newFiles.length === 0) return;
        const jobNumber = document.getElementById('job_number').value;

        const grid = document.querySelector('.job-files-grid') || createNewFileGrid();

        newFiles.forEach(file => {
            // Create card matching template structure
            const card = document.createElement('div');
            card.className = 'file-card';
            card.dataset.fileId = file.id;

            card.innerHTML = `
                <div class="thumbnail-container no-thumb">
                    <span class="file-extension">${file.filename}</span>
                </div>
                <div class="file-info">
                    <a href="/api/job-files/${file.file_path}" target="_blank">
                        ${file.filename}
                    </a>
                    <span class="timestamp">(Just uploaded)</span>
                    <div class="file-controls">
                        <label class="print-checkbox">
                            <input type="checkbox"
                                   name="jobfile_${file.id}_print_on_jobsheet"
                                   class="print-on-jobsheet autosave-input"
                                   checked>
                            Print on Job Sheet
                        </label>
                        <button class="btn btn-sm btn-danger delete-file" data-file-id="${file.id}">
                            Delete
                        </button>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
    }

    function createNewFileGrid() {
        const noFilesMsg = document.querySelector('#file-list p');
        if (noFilesMsg) noFilesMsg.remove();

        const grid = document.createElement('div');
        grid.className = 'job-files-grid';
        document.querySelector('#file-list').appendChild(grid);
        return grid;
    }
});