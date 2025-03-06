/**
 * delete_job.js - Handles job deletion functionality
 */

document.addEventListener('DOMContentLoaded', () => {
    const deleteJobBtn = document.getElementById('delete-job-btn');
    const confirmDeleteBtn = document.getElementById('confirm-delete-job');
    const deleteJobModal = new bootstrap.Modal(document.getElementById('deleteJobModal'));
    const modalBody = document.getElementById('delete-job-modal-body');
    const jobId = document.getElementById('job_id').value;
    
    // Initialize CSRF token for AJAX requests
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    deleteJobBtn.addEventListener('click', () => {
        // Show the confirmation modal
        deleteJobModal.show();
    });
    
    confirmDeleteBtn.addEventListener('click', async () => {
        try {
            // Call the API to delete the job
            const response = await fetch(`/api/job/${jobId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Success - redirect to kanban view
                deleteJobModal.hide();
                window.location.href = '/kanban/';
            } else {
                // Error - show the error message in the modal
                modalBody.innerHTML = `<div class="alert alert-danger">${data.message || 'An error occurred while deleting the job.'}</div>`;
                // Keep the modal open but disable the confirm button to prevent multiple attempts
                confirmDeleteBtn.disabled = true;
                // Re-enable after 3 seconds
                setTimeout(() => {
                    confirmDeleteBtn.disabled = false;
                }, 3000);
            }
        } catch (error) {
            console.error('Error deleting job:', error);
            modalBody.innerHTML = `<div class="alert alert-danger">An unexpected error occurred. Please try again later.</div>`;
        }
    });
}); 