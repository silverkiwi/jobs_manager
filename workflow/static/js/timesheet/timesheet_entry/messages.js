import { sentMessages } from "./state.js";

function createToastContainer() {
  const container = document.createElement('div');
  container.className = 'toast-container position-fixed top-0 end-0 p-3';
  container.style.zIndex = '1070';
  document.body.appendChild(container);
  return container;
}

/**
 * Renders dynamic messages in a modal or as toast notifications
 * @param {Array} messages - List of messages in the format [{level: "success|error|info", message: "Message"}]
 * @param {string} [containerId] - If provided, shows toast notifications instead of modal
 */
export function renderMessages(messages, containerId) {
  let alertContainer;
  let alertContainerModal = false;
  let modal;

  // Modal logic for when no containerId is provided
  if (!containerId) {
    alertContainer = document.getElementById("alert-modal-body");
    alertContainerModal = true;
    const modalContainer = document.getElementById("alert-container");
    if (!modalContainer || !alertContainerModal) {
      console.error("Alert modal container or body not found.");
      return;
    }
    modal = new bootstrap.Modal(modalContainer);
    modal.show();
    alertContainer.innerHTML = "";
  }

  // Toast container logic for when containerId is provided
  const toastContainer = containerId ? (document.querySelector('.toast-container') || createToastContainer()) : null;

  messages.forEach((msg) => {
    const messageKey = `${msg.level}:${msg.message}`;
    if (sentMessages.has(messageKey) && msg.level !== "success" && !alertContainerModal) {
      return;
    }
    sentMessages.add(messageKey);

    msg.level = msg.level === "error" ? "danger" : msg.level;

    if (containerId) {
      // Toast notification logic
      const toastElement = document.createElement('div');
      toastElement.className = `toast border-0 border-${msg.level}`;
      toastElement.setAttribute('role', 'alert');
      toastElement.setAttribute('aria-live', 'assertive');
      toastElement.setAttribute('aria-atomic', 'true');
      
      toastElement.innerHTML = `
        <div class="toast-header bg-${msg.level} text-white">
          <strong class="me-auto">${msg.level.charAt(0).toUpperCase() + msg.level.slice(1)}</strong>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
          ${msg.message}
        </div>
      `;

      toastContainer.appendChild(toastElement);

      const toast = new bootstrap.Toast(toastElement, {
        animation: true,
        autohide: true,
        delay: 5000
      });

      toast.show();

      toastElement.addEventListener('hidden.bs.toast', () => {
        setTimeout(() => toastElement.remove(), 150);
      });
    } else {
      // Modal alert logic
      const alertDiv = document.createElement("div");
      alertDiv.className = `alert alert-${msg.level} alert-dismissible fade show mt-1`;
      alertDiv.role = "alert";
      alertDiv.innerHTML = `
        ${msg.message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      `;
      alertContainer.appendChild(alertDiv);

      setTimeout(() => {
        alertDiv.classList.remove("show");
        alertDiv.classList.add("fade");
        setTimeout(() => {
          alertDiv.remove();
          if (modal && alertContainer.children.length === 0) {
            modal.hide();
          }
        }, 150);
      }, 5000);
    }
  });
}

// Ensure the window object is available before assigning
if (typeof window !== "undefined") {
  window.renderMessages = renderMessages;
}
