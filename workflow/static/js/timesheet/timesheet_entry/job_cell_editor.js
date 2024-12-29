export class ActiveJobCellEditor {
    init(params) {
        this.value = params.value;
        this.params = params;
        this.jobs = window.timesheet_data.jobs;  // These are already filtered to open jobs

        this.div = document.createElement('div');
        this.div.className = 'job-search-container';

        this.input = document.createElement('input');
        this.input.type = 'text';
        this.input.className = 'job-search-input';
        this.input.placeholder = 'Search open jobs...';

        // Automatically focus the input field when editor is opened
        setTimeout(() => this.input.focus(), 0);

        this.listDiv = document.createElement('div');
        this.listDiv.className = 'job-list';

        // Populate list with open jobs
        this.jobs.forEach(job => {
            const jobRow = document.createElement('div');
            jobRow.className = 'job-row';
            jobRow.textContent = job.job_display_name;
            jobRow.onclick = () => this.selectJob(job);
            this.listDiv.appendChild(jobRow);
        });

        // Filter as user types
        this.input.addEventListener('input', () => {
            const searchTerm = this.input.value.trim().toLowerCase();
            this.listDiv.innerHTML = ''; // Clear previous results

            const filteredJobs = this.jobs
                .filter(job => job.job_display_name.toLowerCase().includes(searchTerm))
                .slice(0, 10); // Limit results to avoid overwhelming the user

            filteredJobs.forEach(job => {
                const jobRow = document.createElement('div');
                jobRow.className = 'job-row';
                jobRow.textContent = job.job_display_name;
                jobRow.onclick = () => this.selectJob(job);
                this.listDiv.appendChild(jobRow);
            });

            // If only one job matches, select it when pressing Enter
            if (filteredJobs.length === 1) {
                this.input.addEventListener('keydown', (event) => {
                    if (event.key === 'Enter' || event.key === 'Tab') {
                        event.stopPropagation();
                        this.selectJob(filteredJobs[0]);
                    }
                });
            }
        });

        this.div.appendChild(this.input);
        this.div.appendChild(this.listDiv);
    }

    selectJob(job) {
        this.value = job.job_number;
        this.params.stopEditing();
    }

    getGui() {
        return this.div;
    }

    getValue() {
        return this.value;
    }

    // Required AG Grid lifecycle methods
    destroy() {
    }

    isPopup() {
        return true;
    }
}