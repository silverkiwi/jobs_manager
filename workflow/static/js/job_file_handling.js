document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-input');
    const dropZone = document.querySelector('.file-drop-zone');
    const fileList = document.getElementById('file-list');

    // Handle file selection
    fileInput.addEventListener('change', handleFiles);

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

    function updateFileList(newFiles) {
        if (!newFiles || newFiles.length === 0) return;
        const jobNumber = document.getElementById('job_number').value;

        const list = document.querySelector('.job-files-list') || createNewFileList();

        newFiles.forEach(filename => {
            const li = document.createElement('li');
            li.innerHTML = `
                <div class="file-info">
                    <a href="/api/job-files/Job-${jobNumber}/${filename}" target="_blank">
                        ${filename}
                    </a>
                    <span class="timestamp">(Just uploaded)</span>
                </div>
            `;
            list.appendChild(li);
        });
    }

    function createNewFileList() {
        const noFilesMsg = document.querySelector('#file-list p');
        if (noFilesMsg) noFilesMsg.remove();

        const ul = document.createElement('ul');
        ul.className = 'job-files-list';
        document.querySelector('#file-list').appendChild(ul);
        return ul;
    }
});