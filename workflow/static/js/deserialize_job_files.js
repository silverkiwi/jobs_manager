    const files = JSON.parse('{{ files_json|safe }}');
    const filesList = document.getElementById("attached-files-list");

    if (files.length > 0) {
        files.forEach(file => {
            const listItem = document.createElement("li");
            listItem.innerHTML = `<a href="${file.url}" target="_blank">${file.filename}</a>
                                  <span class="text-muted"> (Uploaded: ${file.uploaded_at})</span>`;
            filesList.appendChild(listItem);
        });
    } else {
        filesList.innerHTML = "<li>No files uploaded for this job.</li>";
    }
