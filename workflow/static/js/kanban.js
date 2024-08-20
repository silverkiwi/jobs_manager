window.addEventListener('load', function() {
    // Estimate the height of a single job card in pixels
    let jobHeight = 100;

    // Loop through all the columns and fetch jobs for each status
    document.querySelectorAll('.column').forEach(column => {
        let status = column.id;

        // Calculate available height for the container
        let containerHeight = column.clientHeight;
        let maxJobs = Math.floor(containerHeight / jobHeight);

        // Fetch and display jobs dynamically for each column
        fetchJobs(status, maxJobs);
    });
});

console.log("Kanban.js loaded");

function fetchJobs(status, maxJobs) {
    console.log(`fetchJobs called for status: ${status}, maxJobs: ${maxJobs}`);
    fetch(`/kanban/fetch_jobs/${status}/?max_jobs=${maxJobs}`)
    .then(response => {
        console.log(`Response for ${status}:`, response);
        return response.json();
    })
    .then(data => {
        console.log(`Data for ${status}:`, data);
        let container = document.querySelector(`#${status} .job-container`);
        if (!container) {
            console.error(`Container for status ${status} not found`);
            return;
        }
        container.innerHTML = ''; // Clear existing cards

        if (data.jobs.length === 0) {
            console.log(`No jobs found for status: ${status}`);
            let noJobs = document.createElement('p');
            noJobs.textContent = 'No jobs in this status';
            container.appendChild(noJobs);
            return;
        }

        data.jobs.forEach(job => {
            let card = document.createElement('div');
            card.className = 'card';
            card.setAttribute('data-id', job.id);
            card.setAttribute('title', job.description);

            let link = document.createElement('a');
            link.href = `/jobs/${job.id}/`;
            link.innerHTML = `<h4>${job.name}</h4><p>${job.description}</p>`;

            card.appendChild(link);
            container.appendChild(card);
        });

        if (data.total > maxJobs) {
            let tooMany = document.createElement('p');
            tooMany.textContent = 'Too many to display';
            container.appendChild(tooMany);
        }
    })
    .catch(error => {
        console.error(`Error fetching ${status} jobs:`, error);
    });
}

function filterJobs() {
    let searchInput = document.getElementById('search').value.toLowerCase();
    document.querySelectorAll('.card').forEach(card => {
        let jobName = card.querySelector('h4').textContent.toLowerCase();
        let jobDescription = card.querySelector('p').textContent.toLowerCase();
        if (jobName.includes(searchInput) || jobDescription.includes(searchInput)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

function loadAllColumns() {
    fetchJobs('quoting', 10);
    fetchJobs('approved', 10);
    fetchJobs('in_progress', 10);
    fetchJobs('completed', 10);
    fetchJobs('on_hold', 10);
    fetchJobs('rejected', 10);
    fetchJobs('archived', 10);
}


window.onload = function() {
    console.log("Window loaded, initializing kanban board");
    loadAllColumns();
    initializeDragAndDrop();
};

function initializeDragAndDrop() {
    console.log("Initializing drag and drop");
    const columns = document.querySelectorAll('.column');

    columns.forEach(column => {
        column.addEventListener('dragover', dragOver);
        column.addEventListener('drop', drop);
    });

    // Add drag listeners to job cards after they're loaded
    document.addEventListener('DOMNodeInserted', event => {
        if (event.target.classList && event.target.classList.contains('card')) {
            event.target.addEventListener('dragstart', dragStart);
            event.target.setAttribute('draggable', true);
            console.log("Drag listeners added to new card:", event.target);
        }
    });
}

function dragStart(e) {
    console.log('Drag started:', e.target);
    const jobId = e.target.getAttribute('data-id');
    e.dataTransfer.setData('text/plain', jobId);
    console.log('Set drag data:', jobId);
}

function dragOver(e) {
    e.preventDefault();
    console.log('Drag over:', e.target);
}

function drop(e) {
    e.preventDefault();
    console.log('Drop:', e.target);
    const jobId = e.dataTransfer.getData('text');
    const newStatus = e.target.closest('.column').id;

    console.log(`Attempting to move job ${jobId} to ${newStatus}`);

    // Call your backend to update the job status
    fetch(`/kanban/update_job_status/${jobId}/`, {
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
            console.log(`Job ${jobId} successfully moved to ${newStatus}`);
            // Move the card to the new column
            const card = document.querySelector(`[data-id="${jobId}"]`);
            e.target.closest('.column').querySelector('.job-container').appendChild(card);
        } else {
            console.error('Failed to update job status:', data.error);
        }
    })
    .catch(error => {
        console.error('Error updating job status:', error);
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

console.log("Kanban.js fully loaded");