const filesList = document.getElementById("attached-files-list");

if (files.length > 0) {
  files.forEach((file) => {
    const listItem = document.createElement("li");
    listItem.innerHTML = `
            <div class="file-item">
                ${
                  file.thumbnail_path
                    ? `<img src="/jobs/files/${file.thumbnail_path}" alt="${file.filename}" class="thumb">`
                    : ""
                }
                <a href="${file.url}" target="_blank">${file.filename}</a>
                <span class="text-muted"> (Uploaded: ${file.uploaded_at})</span>
            </div>`;
    filesList.appendChild(listItem);
  });
} else {
  filesList.innerHTML = "<li>No files uploaded for this job.</li>";
}
