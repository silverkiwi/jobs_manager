export class ActiveJobCellEditor {
    init(params) {
        this.value = params.value;
        this.params = params;
        this.jobs = window.timesheet_data.jobs; // Filtered to open jobs

        // Container
        this.div = document.createElement('div');
        this.div.className = 'dropdown position-relative';

        // Input
        this.input = document.createElement('input');
        this.input.type = 'text';
        this.input.className = 'form-control';
        this.input.placeholder = 'Search open jobs...';

        // Automatically focus input
        setTimeout(() => this.input.focus(), 0);

        // List container
        this.listDiv = document.createElement('div');
        this.listDiv.className = 'dropdown-menu p-2 w-100';
        this.listDiv.style.maxHeight = '200px';
        this.listDiv.style.overflowY = 'auto';

        // Populate initial list
        this.populateList(this.jobs);

        // Filter jobs as user types
        this.input.addEventListener('input', () => {
            const searchTerm = this.input.value.trim().toLowerCase();
            const filteredJobs = this.jobs.filter(job =>
                job.job_display_name.toLowerCase().includes(searchTerm)
            );
            this.populateList(filteredJobs.slice(0, 10)); // Limit results to 10
        });

        this.div.appendChild(this.input);
        this.div.appendChild(this.listDiv);
    }

    populateList(jobs) {
        this.listDiv.innerHTML = ''; // Clear previous results

        if (jobs.length === 0) {
            const noResults = document.createElement('div');
            noResults.className = 'dropdown-item text-muted';
            noResults.textContent = 'No jobs found';
            this.listDiv.appendChild(noResults);
            this.listDiv.classList.add('show'); // Ensure dropdown is shown even if empty
            return;
        }

        jobs.forEach(job => {
            const jobRow = document.createElement('a');
            jobRow.className = 'dropdown-item';
            jobRow.href = '#';
            jobRow.textContent = job.job_display_name;
            jobRow.onclick = (e) => {
                e.preventDefault();
                this.selectJob(job);
            };
            this.listDiv.appendChild(jobRow);
        });

        this.listDiv.classList.add('show'); // Ensure the dropdown is visible
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

    destroy() {
        this.listDiv.classList.remove('show'); // Cleanup on destroy
    }

    isPopup() {
        return true;
    }
}
