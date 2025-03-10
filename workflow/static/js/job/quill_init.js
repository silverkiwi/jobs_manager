document.addEventListener("DOMContentLoaded", function () {
    const element = document.getElementById("job_notes_editor");
    const quill = new Quill(element, {
        theme: "snow",
        modules: {
            toolbar: {
                container: [
                    [{ 'header': [1, 2, 3, 4, 5, 6, false] }],

                    ['bold', 'italic', 'underline', 'strike'],

                    [{ 'color': [] }, { 'background': [] }],

                    [{ 'align': [] }],

                    [{ 'list': 'ordered' }, { 'list': 'bullet' }],

                    [{ 'indent': '-1' }, { 'indent': '+1' }],

                    ['blockquote', 'code-block'],

                    ['link', 'clean']
                ]
            },
        },
        placeholder: "Add notes about the job here... (e.g Materials, Gauge, Quantity, etc.)",
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
