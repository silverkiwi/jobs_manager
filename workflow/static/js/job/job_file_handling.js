function attachPrintCheckboxListeners() {
  document.querySelectorAll(".print-on-jobsheet").forEach((checkbox) => {
    checkbox.removeEventListener("change", handlePrintCheckboxChange);
    checkbox.addEventListener("change", handlePrintCheckboxChange);
  });
}

async function handlePrintCheckboxChange(e) {
  const fileId = e.target.dataset.fileId;
  const jobNumber = document.querySelector('[name="job_number"]').value;
  const printOnJobsheet = e.target.checked;
  await updatePrintOnJobsheet(fileId, jobNumber, printOnJobsheet);
}

export async function uploadJobFile(jobNumber, file, method) {
  if (!jobNumber || !file) return;
  
  showUploadFeedback(file.name);
  console.log(`[uploadJobFile] Starting file upload/update for job ${jobNumber} using ${method}`);
  console.log(`[uploadJobFile] File details: name=${file.name}, size=${file.size}, type=${file.type}`);

  const formData = createFileFormData(jobNumber, file);
  try {
    const response = await sendFileRequest(formData, method);
    processUploadResponse(response);
  } catch (error) {
    handleUploadError(error, method);
  }
}

function createFileFormData(jobNumber, file) {
  const formData = new FormData();
  formData.append("job_number", jobNumber);
  formData.append("files", file);
  return formData;
}

async function sendFileRequest(formData, method) {
  const endpoint = "/api/job-files/";
  console.log(`[uploadJobFile] Sending request to ${endpoint} (method=${method})`);

  return fetch(endpoint, {
    method: method,
    headers: {
      "X-CSRFToken": getCSRFToken(),
    },
    body: formData,
  });
}

function getCSRFToken() {
  return document.querySelector('[name="csrfmiddlewaretoken"]').value;
}

async function processUploadResponse(response) {
  const data = await response.json();
  console.log(`[uploadJobFile] Response: status=${response.status}, ok=${response.ok}`, data);
  
  hideUploadFeedback();
  
  if (response.ok) {
    updateFileList(data.uploaded);
  } else {
    console.error(`[uploadJobFile] Failed to upload/update file.`, data);
  }
}

function handleUploadError(error, method) {
  hideUploadFeedback();
  console.error(`[uploadJobFile] Error during ${method} request:`, error);
}

export async function deleteFile(fileId) {
  if (!fileId) return;
  
  console.log(`[deleteFile] Deleting file with ID=${fileId}`);
  if (!confirm("Are you sure you want to delete this file?")) return;

  try {
    const response = await fetch(`/api/job-files/${fileId}`, {
      method: "DELETE",
      headers: {
        "X-CSRFToken": getCSRFToken(),
      },
    });

    handleDeleteResponse(response, fileId);
  } catch (error) {
    console.error("[deleteFile] Error deleting file:", error);
  }
}

function handleDeleteResponse(response, fileId) {
  if (!response.ok) {
    console.error(
      `[deleteFile] Failed to delete file ID=${fileId}. Response status: ${response.status}`
    );
    return;
  }
  
  console.log(`[deleteFile] File with ID=${fileId} deleted successfully`);
  removeFileCard(fileId);
}

function removeFileCard(fileId) {
  const fileCard = document.querySelector(`[data-file-id="${fileId}"]`)?.closest(".file-card");
  if (fileCard) {
    fileCard.remove();
    updateNoFilesMessage();
  }
}

export async function checkExistingJobFile(jobNumber, fileName) {
  console.log(
    `[checkExistingJobFile] Checking if fileName="${fileName}" exists for job ${jobNumber}`,
  );

  try {
    const response = await fetch(`/api/job-files/${jobNumber}`);
    if (!response.ok) return false;

    const files = await response.json();
    return files.some((file) => file.filename === fileName);
  } catch (error) {
    console.error("Error checking existing job file:", error);
    return false;
  }
}

export async function updatePrintOnJobsheet(
  fileId,
  jobNumber,
  printOnJobsheet,
) {
  console.log(
    `[updatePrintOnJobsheet] Starting update for fileId=${fileId}, jobNumber=${jobNumber}, printOnJobsheet=${printOnJobsheet}`,
  );
  try {
    const response = await fetch(`/api/job-files/${jobNumber}`);

    if (!response.ok) {
      console.log(
        `[updatePrintOnJobsheet] Failed to fetch file data. Response status: ${response.status}`,
      );
      return;
    }

    const files = await response.json();
    const fileData = files.find((file) => file.id === fileId);

    if (!fileData) {
      console.log(`[updatePrintOnJobsheet] No file found with ID=${fileId}`);
      return;
    }

    console.log(`[updatePrintOnJobsheet] Found file data:`, fileData);

    const formData = new FormData();
    formData.append("job_number", jobNumber);
    formData.append("filename", fileData.filename);
    formData.append("print_on_jobsheet", printOnJobsheet ? "true" : "false");

    console.log(
      `[updatePrintOnJobsheet] Sending update request with formData:`,
      {
        filename: fileData.filename,
        printOnJobsheet: printOnJobsheet,
      },
    );

    const updateResponse = await fetch(`/api/job-files/`, {
      method: "PUT",
      headers: {
        "X-CSRFToken": document.querySelector('[name="csrfmiddlewaretoken"]')
          .value,
      },
      body: formData,
    });

    if (updateResponse.ok) {
      const data = await updateResponse.json();
      console.log(`[updatePrintOnJobsheet] Update successful:`, data);
      attachPrintCheckboxListeners();
    } else {
      console.log(
        `[updatePrintOnJobsheet] Update failed. Response status: ${updateResponse.status}`,
      );
    }
  } catch (error) {
    console.error("[updatePrintOnJobsheet] Error updating job file:", error);
  }
}

function updateFileList(newFiles) {
  if (!newFiles || newFiles.length === 0) return;

  const grid = document.querySelector(".job-files-grid") || createNewFileGrid();

  newFiles.forEach((file) => {
    // Ignore summary in visual list
    if (file.filename === "JobSummary.pdf") return;

    const card = document.createElement("div");
    card.className = "file-card";
    card.dataset.fileId = file.id;

    card.innerHTML = `
            <div class="thumbnail-container no-thumb">
                <span class="file-extension">${getFileExtension(file.filename)}</span>
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
                        ${file.print_on_jobsheet ? "checked" : ""}>
                    Print on Job Sheet
                </label>
                <button class="btn btn-sm btn-danger delete-file" data-file-id="${file.id}">
                    Delete
                </button>
            </div>
        `;

    grid.appendChild(card);
  });

  attachPrintCheckboxListeners();
  updateNoFilesMessage();
}

function createNewFileGrid() {
  const fileList = document.querySelector("#file-list");
  
  // Remove any existing messages
  const noFilesMsg = fileList.querySelector("p");
  if (noFilesMsg) noFilesMsg.remove();

  const grid = document.createElement("div");
  grid.className = "job-files-grid";
  fileList.appendChild(grid);
  
  updateNoFilesMessage();
  return grid;
}

// Get file extension to display in the file card
function getFileExtension(filename) {
  const parts = filename.split('.');
  return parts.length > 1 ? `.${parts.pop().toUpperCase()}` : filename;
}

function showUploadFeedback(filename) {
  const feedbackEl = getOrCreateFeedbackElement();
  updateFeedbackFilename(feedbackEl, filename);
  feedbackEl.style.display = 'flex';
}

function getOrCreateFeedbackElement() {
  let feedbackEl = document.getElementById('file-upload-feedback');
  
  if (feedbackEl) return feedbackEl;
  
  feedbackEl = createFeedbackElement();
  ensureFeedbackStyles();
  document.body.appendChild(feedbackEl);
  
  return feedbackEl;
}

function createFeedbackElement() {
  const element = document.createElement('div');
  element.id = 'file-upload-feedback';
  element.className = 'upload-feedback';
  
  element.innerHTML = `
    <div class="upload-spinner">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>
    <div>Uploading file</div>
    <div class="upload-filename"></div>
  `;
  
  return element;
}

function ensureFeedbackStyles() {
  if (document.getElementById('upload-feedback-styles')) return;
  
  const style = document.createElement('style');
  style.id = 'upload-feedback-styles';
  style.textContent = `
    .upload-feedback {
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(255, 255, 255, 0.9);
      border-radius: 5px;
      padding: 20px;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
      z-index: 9999;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .upload-spinner {
      margin-bottom: 15px;
    }
    .upload-filename {
      font-weight: bold;
      max-width: 250px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  `;
  document.head.appendChild(style);
}

function updateFeedbackFilename(feedbackEl, filename) {
  feedbackEl.querySelector('.upload-filename').textContent = filename;
}

function hideUploadFeedback() {
  const feedbackEl = document.getElementById('file-upload-feedback');
  if (feedbackEl) {
    feedbackEl.style.display = 'none';
  }
}

// Verify the existence of real files (excluding JobSummary.pdf)
function updateNoFilesMessage() {
  const grid = document.querySelector(".job-files-grid");
  const fileList = document.querySelector("#file-list");
  
  if (!fileList) return;
  
  const hasVisibleFiles = grid && grid.querySelector('.file-card:not(.d-none)');
  const existingMessage = fileList.querySelector(".alert.alert-info");
  
  if (hasVisibleFiles) {
    if (existingMessage) existingMessage.remove();
    return;
  }
  
  // No visible files case
  if (existingMessage) return; // Message already exists
  
  // Clean up empty grid
  if (grid && grid.children.length === 0) {
    grid.remove();
  }
  
  // Create and add the message
  const noFilesMsg = createNoFilesMessage();
  fileList.appendChild(noFilesMsg);
}

function createNoFilesMessage() {
  const message = document.createElement("div");
  message.className = "alert alert-info";
  message.innerHTML = '<i class="bi bi-info-circle me-2"></i>No files attached to this job.';
  return message;
}

document.addEventListener("DOMContentLoaded", function () {
  attachPrintCheckboxListeners();
  updateNoFilesMessage();
  setupFileUploadEvents();
  setupDocumentEvents();
});

function setupFileUploadEvents() {
  const fileInput = document.getElementById("file-input");
  if (fileInput) {
    fileInput.addEventListener("change", handleFileInputChange);
  }

  const dropZone = document.querySelector(".file-drop-zone");
  if (dropZone) {
    setupDropZoneEvents(dropZone);
  }
}

function setupDropZoneEvents(dropZone) {
  dropZone.addEventListener("drop", handleFileDrop);
  
  ["dragenter", "dragover"].forEach(event => 
    dropZone.addEventListener(event, () => dropZone.classList.add("drag-over"), false)
  );
  
  ["dragleave", "drop"].forEach(event => 
    dropZone.addEventListener(event, () => dropZone.classList.remove("drag-over"), false)
  );
}

async function handleFileInputChange(event) {
  const files = event.target.files;
  if (!files.length) return;
  
  const jobNumber = document.querySelector('[name="job_number"]').value;
  await processFiles(files, jobNumber);
}

async function handleFileDrop(e) {
  e.preventDefault();
  const files = e.dataTransfer.files;
  if (!files.length) return;
  
  const jobNumber = document.querySelector('[name="job_number"]').value;
  await processFiles(files, jobNumber);
}

async function processFiles(files, jobNumber) {
  for (const file of files) {
    if (file.size === 0) {
      alert(`Cannot upload 0-byte file: ${file.name}`);
      continue;
    }

    const fileExists = await checkExistingJobFile(jobNumber, file.name);
    await uploadJobFile(jobNumber, file, fileExists ? "PUT" : "POST");
  }
}

function setupDocumentEvents() {
  document.addEventListener("click", function(e) {
    if (e.target.classList.contains("delete-file")) {
      const fileId = e.target.dataset.fileId;
      if (fileId) deleteFile(fileId);
    }
  });
}
