console.log('kanban.js load started');

document.addEventListener('DOMContentLoaded', function () {
    console.log('Script loaded and DOM fully loaded');

    fetchStatusValues(); // Fetch statuses dynamically

    // Initialize search functionality
    document.getElementById('search').addEventListener('input', filterJobs);
});

function fetchStatusValues() {
    fetch('/api/fetch_status_values/')
        .then(response => response.json())
        .then(statuses => {
            if (statuses && typeof statuses === 'object') {
                loadAllColumns(statuses);
            } else {
                console.error('Unexpected data structure:', statuses);
            }
        })
        .catch(error => console.error('Error fetching status values:', error));
}

function loadAllColumns(statuses) {
    if (!statuses || typeof statuses !== 'object') {
        console.error('Invalid statuses data:', statuses);
        return;
    }
    for (const status_key in statuses) {
        if (statuses.hasOwnProperty(status_key)) {
            fetchJobs(status_key);
        }
    }
}

function fetchJobs(status) {
    fetch(`/kanban/fetch_jobs/${status}/`)
        .then(response => response.json())
        .then(data => {
            const container = document.querySelector(`#${status} .job-list`);
            if (!container) {
                console.error(`Container not found for status: ${status}`);
                return;
            }

            container.innerHTML = ''; // Clear existing cards

            data.jobs.forEach(job => {
                let card = createJobCard(job);
                container.appendChild(card);
            });

            updateColumnHeader(status); // Update the header after fetching jobs

            // Initialize SortableJS for drag-and-drop functionality
            new Sortable(container, {
                group: 'shared',
                animation: 150,
                ghostClass: 'job-card-ghost',
                chosenClass: 'job-card-chosen',
                dragClass: 'job-card-drag',
                onEnd: function (evt) {
                    const itemEl = evt.item; // The dragged element
                    const oldStatus = evt.from.closest('.kanban-column').id; // Source column ID
                    const newStatus = evt.to.closest('.kanban-column').id; // Destination column ID
                    const jobId = itemEl.getAttribute('data-id'); // Job ID of the moved item

                    if (!oldStatus || !newStatus) {
                        console.error('Could not determine old or new column status for job move.');
                        return;
                    }

                    updateJobStatus(jobId, newStatus);

                    // Update headers for both source and destination columns
                    updateColumnHeader(oldStatus);
                    updateColumnHeader(newStatus);
                }
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
    card.setAttribute('data-job-name', job.name || '');
    card.setAttribute('data-client-name', job.client ? job.client.name : '');
    card.setAttribute('data-job-description', job.description || '');
    card.setAttribute('data-job-number', job.job_number);
    card.innerHTML = `
        <h3><a href="/job/${job.id}/">Job ${job.job_number}: ${job.name}</a></h3>
        <p>${job.description ?? ''}</p>
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
        if (!data.success) {
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
    document.querySelectorAll('.kanban-column').forEach(column => {
        const status = column.id;
        const jobCards = column.querySelectorAll('.job-card');
        jobCards.forEach(card => {
            const jobName = card.dataset.jobName || '';
            const jobDescription = card.dataset.jobDescription || '';
            const clientName = card.dataset.clientName || '';
            const jobNumber = card.dataset.jobNumber || '';

            const combinedText = [jobName, jobDescription, clientName, jobNumber].join(' ').toLowerCase();

            if (combinedText.includes(searchTerm)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
        updateColumnHeader(status); // Update the header for each column after filtering
    });
}

// Function to update column headers with total and filtered job counts
function updateColumnHeader(status) {
    const column = document.getElementById(status);
    if (!column) {
        console.error(`Column not found for status: ${status}`);
        return;
    }

    const jobCards = column.querySelectorAll('.job-card');
    const visibleCards = Array.from(jobCards).filter(card => card.style.display !== 'none');

    const header = column.querySelector('.column-header'); // Use the correct class name
    if (header) {
        const totalDisplayed = Math.min(visibleCards.length, 10); // Still limit visible jobs to 10
        header.textContent = `${header.textContent.split('(')[0].trim()} (${totalDisplayed} of ${jobCards.length})`;
    } else {
        console.error(`Header not found in column: ${status}`);
    }
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
