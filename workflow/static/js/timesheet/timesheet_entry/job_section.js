/**
 * Filters the list of jobs to include only those related to the given time entries.
 * 
 * @param {Array<Object>} jobs - The list of all jobs.
 * @param {Array<Object>} timeEntries - The list of time entries to filter against.
 * @returns {Array<Object>} The filtered list of jobs related to the time entries.
 * 
 * Purpose:
 * - Ensures only jobs with matching `job_number` from the time entries are included.
 * 
 * Example:
 * const jobs = [{ job_number: 1 }, { job_number: 2 }];
 * const timeEntries = [{ job_number: 1 }];
 * const filteredJobs = filterRelatedJobs(jobs, timeEntries);
 * console.log(filteredJobs); // [{ job_number: 1 }]
 */
function filterRelatedJobs(jobs, timeEntries) {
    const relatedJobNumbers = new Set(timeEntries.map(entry => entry.job_number));
    return jobs.filter(job => relatedJobNumbers.has(job.job_number));
}

/**
 * Fetches jobs and time entries from the server via an AJAX request and updates the job list.
 * 
 * Purpose:
 * - Retrieves data related to jobs and time entries from the backend.
 * - Filters jobs to include only those related to the time entries.
 * - Updates the job list dynamically based on the response.
 * 
 * Error Handling:
 * - Logs detailed error information if the AJAX request fails.
 * - Warns if the response is missing required data (`jobs` or `time_entries`).
 * 
 * Dependencies:
 * - Requires jQuery for AJAX handling.
 * - Requires `filterRelatedJobs` and `updateJobsList` functions.
 * 
 * Example:
 * fetchJobs();
 */
export function fetchJobs() {
    console.log('Fetching jobs...');
    $.ajax({
        url: window.location.pathname,
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        success: function (response) {
            console.log('AJAX response received:', response);

            if (response.jobs && response.time_entries) {
                const relatedJobs = filterRelatedJobs(
                    response.jobs,
                    response.time_entries
                );

                console.log('Filtered related jobs:', relatedJobs);
                updateJobsList(relatedJobs, 'load');
            } else {
                console.warn('Jobs or time_entries missing in response.');
            }
        },
        error: function (xhr, status, error) {
            console.error('Error fetching jobs:', error, 'Response:', xhr.responseText);
        }
    });
}

function getStatusIcon(status) {
    const icons = {
        'quoting': '📝',
        'approved': '✅',
        'rejected': '❌', 
        'in_progress': '🚧',
        'on_hold': '⏸️',
        'special': '⭐',
        'completed': '✔️',
        'archived': '📦'
    };
    return icons[status] || '';
}

/**
 * Updates the current list of jobs displayed on the page based on the specified action.
 * 
 * @param {Array<Object>} jobs - The list of jobs to update or modify.
 * @param {string} action - The action to perform: 'load', 'add', or 'remove'.
 * 
 * Purpose:
 * - 'load': Replaces the current job list entirely.
 * - 'add': Adds new jobs to the current list, avoiding duplicates.
 * - 'remove': Removes specified jobs from the current list.
 * 
 * Business Logic:
 * - Ensures the UI reflects the current state of jobs, showing a message if the list is empty.
 * - Dynamically updates the DOM by rendering job items or an alert message.
 * 
 * Example:
 * updateJobsList([{ id: 1, job_display_name: "Job A", client_name: "Client A" }], 'load');
 */
let currentJobs = [];
export function updateJobsList(jobs, action) {
    console.log('Updating jobs list with:', jobs);

    const jobsList = document.getElementById('jobs-list');
    if (!jobsList) {
        console.error('Element #jobs-list not found in the DOM.');
        return;
    }

    if (action === 'load') {
        currentJobs = jobs;
    } else if (action === 'add') {
        jobs.forEach(job => {
            if (!currentJobs.some(currentJob => currentJob.id === job.id)) {
                currentJobs.push(job);
            }
        });
    } else if (action === 'remove') {
        jobs.forEach(job => {
            currentJobs = currentJobs.filter(currentJob => currentJob.id !== job.id);
        });
    }

    jobsList.innerHTML = '';

    if (currentJobs.length === 0) {
        jobsList.innerHTML = `
            <div id="no-jobs-alert" class="alert alert-info" role="alert">
                No jobs are currently loaded.
            </div>`;
        return;
    }

    currentJobs.forEach(job => {
        const statusIcon = getStatusIcon(job.job_status);
        const hoursExceeded = job.hours_spent > job.estimated_hours;
        const warningMessage = hoursExceeded ? `<small style="color: red">⚠ Exceeds estimated hours</small>` : '';

        const jobItem = document.createElement('div');
        jobItem.className = 'accordion-item';
        jobItem.innerHTML = `
            <h2 class="accordion-header" id="heading-${job.id}">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-${job.id}">
                    ${statusIcon} <strong>${job.job_display_name}</strong>
                </button>
            </h2>
            <div id="collapse-${job.id}" class="accordion-collapse collapse">
                <div class="accordion-body">
                    <p><strong>Status:</strong> ${job.job_status.charAt(0).toUpperCase() + job.job_status.slice(1)}</p>
                    <hr>
                    <p><strong>Estimated Hours:</strong> ${job.estimated_hours}</p>
                    <hr>
                    <p><strong>Hours Spent:</strong> ${job.hours_spent} ${warningMessage}</p>
                </div>
            </div>
        `;
        jobsList.appendChild(jobItem);
    });
}
