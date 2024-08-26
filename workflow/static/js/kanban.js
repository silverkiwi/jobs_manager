console.log('kanban.js load started');

document.addEventListener('DOMContentLoaded', function () {
    console.log('Script loaded and DOM fully loaded');

    fetchStatusValues();  // Fetch statuses dynamically

    // Initialize search functionality
    document.getElementById('search').addEventListener('input', filterJobs);
});

function fetchStatusValues() {
    fetch('/api/fetch_status_values/')
        .then(response => response.json())
        .then(data => {
            const statuses = data.status_choices;  // Use the fetched statuses
            loadAllColumns(statuses);  // Pass the statuses to the function
        })
        .catch(error => console.error('Error fetching status values:', error));
}

// Function to fetch jobs and populate the columns
function loadAllColumns(statuses) {
    console.log('Loading all columns');
    statuses.forEach(status => {
        const status_key = status[0];  // Extract the status key (e.g., 'quoting')
        fetchJobs(status_key);  // Use the key to fetch jobs and update the DOM
    });
}

function fetchJobs(status) {
    fetch(`/kanban/fetch_jobs/${status}/`)
        .then(response => response.json())
        .then(data => {
            const container = document.querySelector(`#${status} .job-list`);
            if (!container) {
                console.error(`Container not found for status: ${status}`);
                return;  // Exit if the container is null
            }

            container.innerHTML = ''; // Clear existing cards

            if (data.jobs.length === 0) {
                let noJobs = document.createElement('p');
                noJobs.textContent = 'No jobs in this status';
                noJobs.className = 'no-jobs';
                container.appendChild(noJobs);
            } else {
                data.jobs.forEach(job => {
                    let card = createJobCard(job);
                    container.appendChild(card);
                });
            }

            // Initialize SortableJS for drag-and-drop functionality, even if the container is empty
            new Sortable(container, {
                group: 'shared',
                animation: 150,
                ghostClass: 'job-card-ghost',
                chosenClass: 'job-card-chosen',
                dragClass: 'job-card-drag',
                onEnd: function (evt) {
                    const itemEl = evt.item;
                    const newStatus = evt.to.closest('.kanban-column').id;
                    const jobId = itemEl.getAttribute('data-id');
                    updateJobStatus(jobId, newStatus);

                    // Update "No jobs in this status" message dynamically after drag-and-drop
                    updateColumnPlaceholder(evt.from);
                    updateColumnPlaceholder(evt.to);
                }
            });
        })
        .catch(error => {
            console.error(`Error fetching ${status} jobs:`, error);
        });
}

function updateColumnPlaceholder(container) {
    const jobCards = container.querySelectorAll('.job-card');
    const noJobsMessage = container.querySelector('.no-jobs');

    if (jobCards.length === 0) {
        if (!noJobsMessage) {
            let noJobs = document.createElement('p');
            noJobs.textContent = 'No jobs in this status';
            noJobs.className = 'no-jobs';
            container.appendChild(noJobs);
        }
    } else {
        if (noJobsMessage) {
            noJobsMessage.remove();
        }
    }
}

// Function to create a job card element
function createJobCard(job) {
    let card = document.createElement('div');
    card.className = 'job-card';
    card.setAttribute('data-id', job.id);
    card.innerHTML = `
        <h3><a href="/jobs/${job.id}/edit/">${job.name}</a></h3>
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
        }
    })
    .catch(error => {
        console.error('Error updating job status:', error);
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
