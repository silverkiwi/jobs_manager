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
  console.log(
    `[uploadJobFile] Starting file upload/update for job ${jobNumber} using ${method}`,
  );
  console.log(
    `[uploadJobFile] File details: name=${file.name}, size=${file.size}, type=${file.type}`,
  );

  // Just sending the file data and letting the print_on_jobsheet to be handled with the listeners
  const formData = new FormData();
  formData.append("job_number", jobNumber);
  formData.append("files", file);

  try {
    const endpoint = "/api/job-files/";
    console.log(
      `[uploadJobFile] Sending request to ${endpoint} (method=${method})`,
    );

    const response = await fetch(endpoint, {
      method: method,
      headers: {
        "X-CSRFToken": document.querySelector('[name="csrfmiddlewaretoken"]')
          .value,
      },
      body: formData,
    });

    const data = await response.json();
    console.log(
      `[uploadJobFile] Response: status=${response.status}, ok=${response.ok}`,
      data,
    );

    if (response.ok) {
      updateFileList(data.uploaded);
    } else {
      console.error(`[uploadJobFile] Failed to ${method} file.`, data);
    }
  } catch (error) {
    console.error(`[uploadJobFile] Error during ${method} request:`, error);
  }
}

export async function deleteFile(fileId) {
  console.log(`[deleteFile] Deleting file with ID=${fileId}`);
  if (!confirm("Are you sure you want to delete this file?")) return;

  try {
    const response = await fetch(`/api/job-files/${fileId}`, {
      method: "DELETE",
      headers: {
        "X-CSRFToken": document.querySelector('[name="csrfmiddlewaretoken"]')
          .value,
      },
    });

    if (response.ok) {
      console.log(`[deleteFile] File with ID=${fileId} deleted successfully`);
      document
        .querySelector(`[data-file-id="${fileId}"]`)
        ?.closest(".file-card")
        ?.remove();
    } else {
      console.error(
        `[deleteFile] Failed to delete file ID=${fileId}. Response status: ${response.status}`,
      );
    }
  } catch (error) {
    console.error("[deleteFile] Error deleting file:", error);
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
    if (file.filename === "JobSummary.pdf") return;

    const card = document.createElement("div");
    card.className = "file-card";
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
}

function createNewFileGrid() {
  const noFilesMsg = document.querySelector("#file-list p");
  if (noFilesMsg) noFilesMsg.remove();

  const grid = document.createElement("div");
  grid.className = "job-files-grid";
  document.querySelector("#file-list").appendChild(grid);
  return grid;
}

document.addEventListener("DOMContentLoaded", function () {
  attachPrintCheckboxListeners();

  const fileInput = document.getElementById("file-input");
  const dropZone = document.querySelector(".file-drop-zone");

  fileInput.addEventListener("change", async function (event) {
    const files = event.target.files;
    const jobNumber = document.querySelector('[name="job_number"]').value;

    for (let file of files) {
      const fileExists = await checkExistingJobFile(jobNumber, file.name);
      await uploadJobFile(jobNumber, file, fileExists ? "PUT" : "POST");
    }
  });

  dropZone.addEventListener("drop", async function (e) {
    e.preventDefault();
    const files = e.dataTransfer.files;
    const jobNumber = document.querySelector('[name="job_number"]').value;

    for (let file of files) {
      if (file.size === 0) {
        alert(`Cannot upload 0-byte file: ${file.name}`);
        continue;
      }

      const fileExists = await checkExistingJobFile(jobNumber, file.name);
      await uploadJobFile(jobNumber, file, fileExists ? "PUT" : "POST");
    }
  });

  ["dragenter", "dragover"].forEach((event) =>
    dropZone.addEventListener(
      event,
      () => dropZone.classList.add("drag-over"),
      false,
    ),
  );
  ["dragleave", "drop"].forEach((event) =>
    dropZone.addEventListener(
      event,
      () => dropZone.classList.remove("drag-over"),
      false,
    ),
  );

  document.addEventListener("click", function (e) {
    if (e.target.classList.contains("delete-file")) {
      const fileId = e.target.dataset.fileId;
      if (fileId) deleteFile(fileId);
    }
  });
});
