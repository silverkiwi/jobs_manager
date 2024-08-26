document.addEventListener('DOMContentLoaded', function () {
    // Initialize SortableJS for drag-and-drop functionality
    const columns = document.querySelectorAll('.job-list');
    columns.forEach(column => {
        Sortable.create(column, {
            group: 'kanban', // Allows dragging between columns
            animation: 150,
            easing: "cubic-bezier(1, 0, 0, 1)", // Smooth easing function
            dragClass: "job-card-dragging",
            ghostClass: "job-card-ghost",
            onEnd: function (evt) {
                const itemEl = evt.item;  // dragged HTMLElement
                const newStatus = evt.to.closest('.kanban-column').id;  // new status column ID

                // Update job status in the backend
                const jobId = itemEl.getAttribute('data-id');
                updateJobStatus(jobId, newStatus);
            }
        });
    });

    // Load jobs into each column
    loadAllColumns();

    // Set up search functionality
    document.getElementById('search').addEventListener('input', filterJobs);
});

// Function to fetch jobs and populate the columns
function loadAllColumns() {
    const statuses = ['quoting', 'approved', 'in_progress', 'completed', 'awaiting_materials', 'on_hold', 'rejected', 'archived'];
    statuses.forEach(status => {
        fetchJobs(status);
    });
}

// Function to fetch jobs for a specific status
function fetchJobs(status) {
    fetch(`/kanban/fetch_jobs/${status}/`)
        .then(response => response.json())
        .then(data => {
            const container = document.querySelector(`#${status} .job-list`);
            container.innerHTML = ''; // Clear existing cards

            if (data.jobs.length === 0) {
                let noJobs = document.createElement('p');
                noJobs.textContent = 'No jobs in this status';
                noJobs.className = 'no-jobs';
                container.appendChild(noJobs);
                return;
            }

            data.jobs.forEach(job => {
                let card = createJobCard(job);
                container.appendChild(card);
            });
        })
        .catch(error => {
            console.error(`Error fetching ${status} jobs:`, error);
        });
}

// Function to create a job card element
function createJobCard(job) {
    let card = document.createElement('div');
    card.className = 'job-card';
    card.setAttribute('data-id', job.id);
    card.innerHTML = `
        <h3>${job.name}</h3>
        <p>${job.description}</p>
    `;
    return card;
}

// Function to update job status in the backend
function updateJobStatus(jobId, newStatus) {
    fetch(`/jobs/${jobId}/update_status/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ status: newStatus })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Job status updated successfully');
        } else {
            console.error('Failed to update job status:', data.error);
            // You might want to move the item back to its original position or refresh the board
        }
    })
    .catch(error => {
        console.error('Error updating job status:', error);
        // You might want to move the item back to its original position or refresh the board
    });
}

// Function to filter jobs based on search input
function filterJobs() {
    const searchTerm = document.getElementById('search').value.toLowerCase();
    document.querySelectorAll('.job-card').forEach(card => {
        const jobName = card.querySelector('h3').textContent.toLowerCase();
        const jobDescription = card.querySelector('p').textContent.toLowerCase();
        if (jobName.includes(searchTerm) || jobDescription.includes(searchTerm)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });

    // Show/hide "No jobs in this status" message
    document.querySelectorAll('.kanban-column').forEach(column => {
        const visibleCards = column.querySelectorAll('.job-card:not([style*="display: none"])');
        const noJobsMessage = column.querySelector('.no-jobs');

        if (visibleCards.length === 0) {
            if (!noJobsMessage) {
                const newMessage = document.createElement('p');
                newMessage.textContent = 'No jobs in this status';
                newMessage.className = 'no-jobs';
                column.querySelector('.job-list').appendChild(newMessage);
            } else {
                noJobsMessage.style.display = '';
            }
        } else if (noJobsMessage) {
            noJobsMessage.style.display = 'none';
        }
    });
}

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}