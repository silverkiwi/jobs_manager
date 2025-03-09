document.addEventListener("DOMContentLoaded", function () {
    const element = document.getElementById("job_notes_editor");
    const quill = new Quill(element, {
        theme: "snow",
        modules: {
            toolbar: "#job_notes_toolbar"
        },
        placeholder: "Add notes about the job here..."
    });

    const notesInput = document.getElementById("job_notes");
    if (notesInput.value) {
        try {
            quill.root.innerHTML = notesInput.value;
        } catch (e) {
            console.error("Error on loading notes:", e);
        }
    }

    quill.on("text-change", () => {
        const notesContent = quill.root.innerHTML;
        notesInput.value = notesContent;

        const event = new Event("blur", { bubbles: true });
        notesInput.dispatchEvent(event);
    });
});
