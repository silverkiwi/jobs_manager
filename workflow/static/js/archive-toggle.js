/**
 * Archive visibility toggle functionality
 */
document.addEventListener("DOMContentLoaded", function () {
  const toggleArchiveBtn = document.getElementById("toggleArchive");

  if (toggleArchiveBtn) {
    // Check localStorage for saved preference
    const archiveVisible = localStorage.getItem("archiveVisible") === "true";
    const archiveContainer = document.getElementById("archiveContainer");
    const toggleIcon = toggleArchiveBtn.querySelector("i");

    // Apply saved state on page load
    if (archiveVisible) {
      archiveContainer.style.display = "flex";
      toggleIcon.classList.remove("bi-chevron-down");
      toggleIcon.classList.add("bi-chevron-up");
    }

    // Handle toggle click
    toggleArchiveBtn.addEventListener("click", function () {
      const isCurrentlyVisible = archiveContainer.style.display !== "none";

      if (isCurrentlyVisible) {
        archiveContainer.style.display = "none";
        toggleIcon.classList.remove("bi-chevron-up");
        toggleIcon.classList.add("bi-chevron-down");
        localStorage.setItem("archiveVisible", "false");
      } else {
        archiveContainer.style.display = "flex";
        toggleIcon.classList.remove("bi-chevron-down");
        toggleIcon.classList.add("bi-chevron-up");
        localStorage.setItem("archiveVisible", "true");
      }
    });
  }
});
