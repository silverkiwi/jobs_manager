window.addEventListener('load', function() {
    // Estimate the height of a single job card in pixels
    let jobHeight = 100;

    // Get the containers for the Rejected and Paid columns
    let rejectedContainer = document.getElementById('rejected');
    let paidContainer = document.getElementById('paid');

    // Calculate the available height for each container
    let rejectedHeight = rejectedContainer.clientHeight;
    let paidHeight = paidContainer.clientHeight;

    // Determine the maximum number of jobs that can be displayed based on the available height
    let maxRejectedJobs = Math.floor(rejectedHeight / jobHeight);
    let maxPaidJobs = Math.floor(paidHeight / jobHeight);

    // Fetch and display jobs dynamically for Rejected and Paid columns
    fetchJobs('rejected', maxRejectedJobs);
    fetchJobs('paid', maxPaidJobs);
});

// Function to fetch and populate job cards in the specified column
function fetchJobs(status, maxJobs) {
    fetch(`/kanban/fetch_jobs/${status}/?max_jobs=${maxJobs}`)
    .then(response => {
        console.log(`Response for ${status}:`, response);
        return response.json();
    })
    .then(data => {
        console.log(`Data for ${status}:`, data);
        let container = document.getElementById(status);

        // Clear only the job cards, leaving the header intact
        let cards = container.querySelectorAll('.card');
        cards.forEach(card => card.remove());

        // Loop through the jobs and add them to the container
        data.jobs.forEach(job => {
            let card = document.createElement('div');
            card.className = 'card';
            card.setAttribute('data-id', job.id);

            let link = document.createElement('a');
            link.href = `/jobs/${job.id}/`;
            link.innerHTML = `<h3>${job.title}</h3><p>${job.description}</p>`;

            card.appendChild(link);
            container.appendChild(card);
        });

        // If there are more jobs than can be displayed, add a "Too many to display" message
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


// Example function to load all columns (this can be modified to suit your needs)
function loadAllColumns() {
    fetchJobs('quoting', 10);  // Fetch 10 jobs for the "Quoting" column
    fetchJobs('awaiting_approval', 10);
    fetchJobs('awaiting_staff_or_materials', 10);
    fetchJobs('in_progress', 10);
    fetchJobs('completed', 10);
    fetchJobs('rejected', 10);
    fetchJobs('paid', 10);
}

// Call the function to load all columns when the page loads
window.onload = loadAllColumns;
