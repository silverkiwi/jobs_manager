function attachPrintCheckboxListeners() {
    document.querySelectorAll('.print-on-jobsheet').forEach(checkbox => {
        checkbox.removeEventListener('change', handlePrintCheckboxChange);
        checkbox.addEventListener('change', handlePrintCheckboxChange);
    });
}

async function handlePrintCheckboxChange(e) {
    const fileId = e.target.dataset.fileId;
    const jobNumber = document.querySelector('[name="job_number"]').value;
    const printOnJobsheet = e.target.checked;

    console.log(`Updating file ${fileId}: print_on_jobsheet=${printOnJobsheet}`);
    await updateJobFile(fileId, jobNumber, printOnJobsheet);
}

export async function uploadJobFile(jobNumber, file, method) {
    console.log(`Starting file upload for job ${jobNumber} using method ${method}`);
    console.log('File details:', {
        name: file.name,
        size: file.size,
        type: file.type
    });

    const formData = new FormData();
    formData.append('job_number', jobNumber);
    formData.append('files', file);

    try {
        console.log('Sending request to /api/job-files/');
        const response = await fetch('/api/job-files/', {
            method: method,
            headers: { 'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]').value },
            body: formData
        });

        const data = await response.json();
        console.log('Response received:', {
            status: response.status,
            ok: response.ok,
            data: data
        });

        if (response.ok) {
            console.log('File upload successful, updating file list');
            updateFileList(data.uploaded);
        } else {
            console.error(`Failed to ${method} file:`, data.message);
            console.error('Response details:', {
                status: response.status,
                statusText: response.statusText,
                data: data
            });
        }
    } catch (error) {
        console.error(`Error during ${method} request:`, error);
        console.error('Error details:', {
            jobNumber,
            fileName: file.name,
            errorMessage: error.message
        });
    }
}

export async function deleteFile(fileId) {
    if (!confirm('Are you sure you want to delete this file?')) return;

    try {
        const response = await fetch(`/api/job-files/${fileId}`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]').value }
        });

        if (response.ok) {
            document.querySelector(`[data-file-id="${fileId}"]`)?.closest('.file-card')?.remove();
        } else {
            console.error(`Failed to delete file ID: ${fileId}. Status: ${response.status}`);
        }
    } catch (error) {
        console.error('Error deleting file:', error);
    }
}

export async function checkExistingJobFile(jobNumber, fileName) {
    try {
        const response = await fetch(`/api/job-files/${jobNumber}`);
        if (!response.ok) return false;

        const files = await response.json();
        return files.some(file => file.filename === fileName);
    } catch (error) {
        console.error('Error checking existing job file:', error);
        return false;
    }
}

export async function updateJobFile(fileId, jobNumber, printOnJobsheet) {
    try {
        console.log(`Updating job file ${fileId} for job ${jobNumber} with print_on_jobsheet=${printOnJobsheet}`);
        console.log('Starting file fetch request');

        const response = await fetch(`/api/job-files/${jobNumber}`);
        console.log('File fetch response:', {
            status: response.status,
            ok: response.ok
        });

        if (!response.ok) {
            console.error(`Failed to fetch job files for job ${jobNumber}`);
            console.error('Response details:', {
                status: response.status,
                statusText: response.statusText
            });
            return;
        }

        const files = await response.json();
        console.log('Files retrieved:', files.length);
        console.log('Files:', files);

        const fileData = files.find(file => file.id === fileId);
        console.log('Found file data:', fileData);

        if (!fileData) {
            console.error(`File ${fileId} not found in job ${jobNumber}`);
            return;
        }

        console.log('Preparing form data for update');
        const formData = new FormData();
        formData.append('job_number', jobNumber);
        formData.append('files', new File([], fileData.filename, { type: fileData.mime_type }));
        formData.append('print_on_jobsheet', printOnJobsheet ? 'true' : 'false');

        console.log('Sending update request');
        const updateResponse = await fetch(`/api/job-files/`, {
            method: 'PUT',
            headers: { 'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]').value },
            body: formData
        });

        console.log('Update response received:', {
            status: updateResponse.status,
            ok: updateResponse.ok
        });

        if (!updateResponse.ok) {
            console.error(`Failed to update file ${fileId}`);
            console.error('Update response details:', {
                status: updateResponse.status,
                statusText: updateResponse.statusText
            });
        } else {
            console.log(`Successfully updated file ${fileId}`);
            const responseData = await updateResponse.json();
            console.log('Update response data:', responseData);
            attachPrintCheckboxListeners();
        }
    } catch (error) {
        console.error('Error updating job file:', error);
        console.error('Error details:', {
            fileId,
            jobNumber,
            errorMessage: error.message
        });
    }
}

function updateFileList(newFiles) {
    if (!newFiles || newFiles.length === 0) return;

    const grid = document.querySelector('.job-files-grid') || createNewFileGrid();

    newFiles.forEach(file => {
        if (file.filename === 'JobSummary.pdf') return;

        const card = document.createElement('div');
        card.className = 'file-card';
        card.dataset.fileId = file.id;

        card.innerHTML = `
            <div class="thumbnail-container no-thumb">
                <span class="file-extension">${file.filename}</span>
            </div>
            <div class="file-info">
                <a href="/api/job-files/${file.file_path}" target="_blank">${file.filename}</a>
                <span class="timestamp">(Just uploaded)</span>
            </div>
            <div class="file-controls">
                <label class="print-checkbox">
                    <input type="checkbox" name="jobfile_${file.id}_print_on_jobsheet"
                        class="print-on-jobsheet" 
                        data-file-id="${file.id}" 
                        ${file.print_on_jobsheet ? 'checked' : ''}>
                    Print on Job Sheet
                </label>
                <button class="btn btn-sm btn-danger delete-file" data-file-id="${file.id}">
                    Delete
                </button>
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

document.addEventListener('DOMContentLoaded', function () {
    attachPrintCheckboxListeners();

    const fileInput = document.getElementById('file-input');
    const dropZone = document.querySelector('.file-drop-zone');

    fileInput.addEventListener('change', async function (event) {
        const files = event.target.files;
        const jobNumber = document.querySelector('[name="job_number"]').value;

        for (let file of files) {
            const fileExists = await checkExistingJobFile(jobNumber, file.name);
            await uploadJobFile(jobNumber, file, fileExists ? 'PUT' : 'POST');
        }
    });

    dropZone.addEventListener('drop', async function (e) {
        e.preventDefault();
        const files = e.dataTransfer.files;
        const jobNumber = document.querySelector('[name="job_number"]').value;

        for (let file of files) {
            const fileExists = await checkExistingJobFile(jobNumber, file.name);
            await uploadJobFile(jobNumber, file, fileExists ? 'PUT' : 'POST');
        }
    });

    ['dragenter', 'dragover'].forEach(event => dropZone.addEventListener(event, () => dropZone.classList.add('drag-over'), false));
    ['dragleave', 'drop'].forEach(event => dropZone.addEventListener(event, () => dropZone.classList.remove('drag-over'), false));

    document.addEventListener('click', function (e) {
        if (e.target.classList.contains('delete-file')) {
            const fileId = e.target.dataset.fileId;
            if (fileId) deleteFile(fileId);
        }
    });
});
