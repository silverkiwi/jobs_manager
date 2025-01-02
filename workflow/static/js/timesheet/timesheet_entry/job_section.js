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
 * Merges new jobs into an existing jobs list or adds them if they don't exist.
 * If a job with the same ID exists, its properties are merged with the new job.
 * If a job doesn't exist, it is added to the list.
 * 
 * @param {Array<Object>} jobsToProcess - Array of new jobs to be processed
 * @param {Array<Object>} currentJobsList - Array of existing jobs
 * @param {number} jobsToProcess[].id - Unique identifier for each job
 * @param {number} currentJobsList[].id - Unique identifier for each existing job
 * @returns {Array<Object>} Updated array of jobs with merged or added items
 */
function mergeOrAddJobs(jobsToProcess, currentJobsList) {
    jobsToProcess.forEach(job => {
        const existingJobIndex = currentJobsList.findIndex(currentJob => currentJob.id === job.id);
        existingJobIndex !== -1 
            ? currentJobsList[existingJobIndex] = { ...currentJobsList[existingJobIndex], ...job }
            : currentJobsList.push(job);
    });
    return currentJobsList;
}

let currentJobs = [];
/**
 * Updates the jobs list and renders the updated section dynamically.
 * @param {Array<Object>} jobs - Jobs to be added or updated.
 * @param {string} action - Action type: 'load', 'add', 'remove', 'update'.
 * @param {Array<Object>} removeJobs - Jobs to be removed (for 'update' action).
 */
export function updateJobsList(jobs, action, removeJobs = []) {
    console.log(`Updating jobs list with ${action}`, { jobs, removeJobs });

    switch (action) {
        case 'load':
            currentJobs = jobs; // Replace the list completely
            break;

        case 'add':
            currentJobs = mergeOrAddJobs(jobs, currentJobs);
            break;

        case 'remove':
            currentJobs = currentJobs.filter(
                currentJob => !jobs.some(job => job.id === currentJob.id)
            );
            break;

        case 'update':
            // Remove outdated jobs
            currentJobs = currentJobs.filter(
                currentJob => !removeJobs.some(job => job.id === currentJob.id)
            );
            // Add or update jobs
            currentJobs = mergeOrAddJobs(jobs, currentJobs);
            console.log('Current jobs after update:', currentJobs);
            break;

        default:
            console.warn(`Unknown action: ${action}`);
    }

    renderJobsSection(currentJobs);
}


/**
 * Renders the jobs section in the DOM based on the current jobs list.
 * @param {Array<Object>} currentJobs - Current list of jobs to render.
 */
function renderJobsSection(currentJobs) {
    const jobsList = document.getElementById('jobs-list');
    if (!jobsList) {
        console.error('Element #jobs-list not found in the DOM.');
        return;
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
        const jobItem = createJobItem(job);
        jobsList.appendChild(jobItem);
    });
}

/**
 * Creates a DOM element for a single job item.
 * @param {Object} job - Job data to render.
 * @returns {HTMLElement} - The DOM element for the job item.
 */
function createJobItem(job) {
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
        <div id="collapse-${job.id}" class="accordion-collapse collapse show">
            <div class="accordion-body">
                <p><strong>Status:</strong> ${job.job_status.charAt(0).toUpperCase() + job.job_status.slice(1)}</p>
                <hr>
                <p><strong>Client:</strong> ${job.client_name}</p>
                <hr>
                <p><strong>Estimated Hours:</strong> ${job.estimated_hours}</p>
                <hr>
                <p><strong>Hours Spent:</strong> ${job.hours_spent} ${warningMessage}</p>
                <hr>
                <p><a href="/job/${job.id}" class="btn btn-primary btn-lg">View Job Details</a></p>
            </div>
        </div>
    `;

    return jobItem;
}
