document.addEventListener("DOMContentLoaded", function () {
  var container = document.getElementById("json-editor");
  var options = {
    mode: "view",
    modes: ["view", "tree"], // Only allow view and tree modes
    onModeChange: function (newMode, oldMode) {
      editor.setMode("view"); // Force view mode if user tries to change
    },
    onEditable: function () {
      return false; // Make it non-editable
    },
  };
  var editor = new JSONEditor(container, options);

  // Get the JSON from the hidden textarea
  var json = JSON.parse(document.getElementById("id_raw_json").value);
  editor.set(json);

  // Disable all buttons in the menu
  editor.aceEditor.setReadOnly(true);
});
