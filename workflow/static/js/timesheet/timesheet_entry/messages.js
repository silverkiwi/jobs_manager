import { sentMessages } from './state.js'


/**
 * Renders dynamic messages in a specified alert container.
 * @param {Array} messages - List of messages in the format [{level: "success|error|info", message: "Message"}].
 * @param {string} containerId - The ID of the alert container to target.
 */
export function renderMessages(messages, containerId = 'alert-container') {
    const alertContainer = document.getElementById(containerId);
    if (!alertContainer) {
        console.error(`Alert container with ID '${containerId}' not found.`);
        return;
    }

    // Add new messages
    messages.forEach(msg => {
        const messageKey = `${msg.level}:${msg.message}`;

        if (sentMessages.has(messageKey) && msg.level !== 'success') {
            return;
        }
        sentMessages.add(messageKey);

        const alertDiv = document.createElement('div');
        msg.level = msg.level === 'error' ? 'danger' : msg.level;
        alertDiv.className = `alert alert-${msg.level} alert-dismissible fade show mt-1`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${msg.message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        alertContainer.appendChild(alertDiv);

        // Add fade out effect after 2 seconds if message level is success
        if (msg.level === 'success') {
            setTimeout(() => {
                alertDiv.classList.remove('show');
                alertDiv.classList.add('fade');
                setTimeout(() => {
                    alertDiv.remove();
                }, 150); // Wait for fade animation to complete
            }, 2000);
        }
    });
}

// Ensure the window object is available before assigning
if (typeof window !== 'undefined') {
    window.renderMessages = renderMessages;
}
