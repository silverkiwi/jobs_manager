import { sentMessages } from "./state.js";

/**
 * Renders dynamic messages in a specified alert container or a modal if no container is specified.
 * @param {Array} messages - List of messages in the format [{level: "success|error|info", message: "Message"}].
 * @param {string} [containerId] - Optional ID of the alert container to target.
 */
export function renderMessages(messages, containerId) {
  let alertContainer;
  let alertContainerModal = false;
  let modal;

  if (containerId) {
    alertContainer = document.getElementById(containerId);
  } else {
    alertContainer = document.getElementById("alert-modal-body");
    alertContainerModal = true;
    const modalContainer = document.getElementById("alert-container");
    if (!modalContainer || !alertContainerModal) {
      console.error("Alert modal container or body not found.");
      return;
    }
    modal = new bootstrap.Modal(modalContainer);
    modal.show();
  }

  if (!alertContainer) {
    console.error(
      `Alert container with ID '${containerId}' not found. Falling back to modal if available.`,
    );
    return;
  }

  alertContainer.innerHTML = "";

  // Add new messages
  messages.forEach((msg) => {
    const messageKey = `${msg.level}:${msg.message}`;

    if (
      sentMessages.has(messageKey) &&
      msg.level !== "success" &&
      !alertContainerModal
    ) {
      return;
    }
    sentMessages.add(messageKey);

    const alertDiv = document.createElement("div");
    msg.level = msg.level === "error" ? "danger" : msg.level;
    alertDiv.className = `alert alert-${msg.level} alert-dismissible fade show mt-1`;
    alertDiv.role = "alert";
    alertDiv.innerHTML = `
            ${msg.message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
    alertContainer.appendChild(alertDiv);

    // Add fade out effect after 5 seconds for all notifications
    setTimeout(() => {
      alertDiv.classList.remove("show");
      alertDiv.classList.add("fade");
      setTimeout(() => {
        alertDiv.remove();
        // Hide modal if this was the last alert
        if (modal && alertContainer.children.length === 0) {
          modal.hide();
        }
      }, 150); // Wait for fade animation to complete
    }, 5000);
  });
}

// Ensure the window object is available before assigning
if (typeof window !== "undefined") {
  window.renderMessages = renderMessages;
}
