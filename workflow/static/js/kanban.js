console.log("kanban.js load started");

let currentPage = {};
let pageSize = 10;

document.addEventListener("DOMContentLoaded", function () {
  console.log("Script loaded and DOM fully loaded");

  fetchStatusValues();

  document
    .getElementById("jobPageSize")
    .addEventListener("change", function () {
      pageSize = parseInt(this.value);
      fetchStatusValues();
    });

  document.getElementById("search").addEventListener("input", function() {
    filterJobs();
    updateColumnCounts();
  });

  // Add event for "Load More" buttons
  document.querySelectorAll(".load-more").forEach((button) => {
    button.addEventListener("click", function () {
      const status = this.getAttribute("data-status");
      if (status) {
        currentPage[status]++;
        loadJobs(status);
      }
    });
  });
});

function fetchStatusValues() {
  fetch("/api/fetch_status_values/")
    .then((response) => response.json())
    .then((statuses) => {
      Object.keys(statuses).forEach((status) => {
        currentPage[status] = 1;
        loadJobs(status, true);
      });

      // After loading statuses, initialize drag and drop functionality
      initializeDragAndDrop();
    })
    .catch((error) => console.error("Error fetching status values:", error));
}

function loadJobs(status, reset = false) {
  const container = document.querySelector(`#${status} .job-list`);
  const countDisplay = document.querySelector(`#${status}-count`);
  const totalDisplay = document.querySelector(`#${status}-total`);
  const loadMoreContainer = document.querySelector(
    `#${status}-load-more-container`,
  );

  if (reset) {
    container.innerHTML = "";
    currentPage[status] = 1;
  }

  fetch(
    `/kanban/fetch_jobs/${status}/?page=${currentPage[status]}&page_size=${pageSize}`,
  )
    .then((response) => response.json())
    .then((data) => {
      data.jobs.forEach((job) => {
        let card = createJobCard(job);
        container.appendChild(card);
      });

      countDisplay.textContent = container.children.length;
      totalDisplay.textContent = data.total_jobs;

      loadMoreContainer.style.display = data.has_next ? "flex" : "none";
      
      updateColumnCounts();

      // Reinitialize SortableJS after loading new jobs
      initializeDragAndDrop();
    })
    .catch((error) => console.error(`Error fetching ${status} jobs:`, error));
}

function createJobCard(job) {
  let card = document.createElement("div");
  card.className = "job-card";
  card.setAttribute("data-id", job.id);
  card.setAttribute("data-job-name", job.name || "");
  card.setAttribute("data-client-name", job.client ? job.client.name : "");
  card.setAttribute("data-job-description", job.description || "");
  card.setAttribute("data-job-number", job.job_number);
  
  card.innerHTML = `
    <div class="job-card-title">${job.job_number}</div>
    <div class="job-card-body small">
      ${job.name}
    </div>
  `;
  
  // Tooltip container (Hidden initially)
  let tooltip = document.createElement("div");
  tooltip.className = "job-tooltip";
  tooltip.textContent = job.description;
  tooltip.style.display = "none";

  // Append tooltip to document body (so it floats near cursor)
  document.body.appendChild(tooltip);

  // Show tooltip on hover
  card.addEventListener("mouseenter", (event) => {
    if (job.description) {
      tooltip.style.display = "block";
      tooltip.style.left = `${event.pageX + 10}px`;
      tooltip.style.top = `${event.pageY + 10}px`;
    }
  });

  // Move tooltip with cursor
  card.addEventListener("mousemove", (event) => {
    tooltip.style.left = `${event.pageX + 10}px`;
    tooltip.style.top = `${event.pageY + 10}px`;
  });

  // Hide tooltip on mouse leave
  card.addEventListener("mouseleave", () => {
    tooltip.style.display = "none";
  });

  card.addEventListener("click", () => {
    window.location.href = `/job/${job.id}/`;
  });

  return card;
}

// Initialize SortableJS to allow moving jobs between columns
function initializeDragAndDrop() {
  document.querySelectorAll(".job-list").forEach((container) => {
    new Sortable(container, {
      group: "shared",
      animation: 150,
      ghostClass: "sortable-ghost",
      chosenClass: "sortable-drag",
      dragClass: "sortable-drag",
      onStart: function() {
        document.querySelectorAll('.kanban-column').forEach(col => {
          col.classList.add('drop-target-potential');
        });
      },
      onEnd: function (evt) {
        const itemEl = evt.item;
        const oldStatus = evt.from.closest(".kanban-column").id;
        const newStatus = evt.to.closest(".kanban-column").id;
        const jobId = itemEl.getAttribute("data-id");

        // Remove a classe de destino potencial
        document.querySelectorAll('.kanban-column').forEach(col => {
          col.classList.remove('drop-target-potential');
        });

        if (!oldStatus || !newStatus || oldStatus === newStatus) {
          return;
        }

        console.log(`Job ${jobId} moved from ${oldStatus} to ${newStatus}`);

        updateJobStatus(jobId, newStatus);

        // Update affected column counters
        updateColumnHeader(oldStatus);
        updateColumnHeader(newStatus);
        
        updateColumnCounts();
      },
    });
  });
}

function updateJobStatus(jobId, newStatus) {
  // Show visual feedback that the status change is in progress
  const jobCard = document.querySelector(`.job-card[data-id="${jobId}"]`);
  if (jobCard) {
    jobCard.style.opacity = "0.7";
    jobCard.classList.add('updating');
  }

  fetch(`/jobs/${jobId}/update_status/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify({ status: newStatus }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        if (jobCard) {
          jobCard.style.opacity = "1";
          jobCard.classList.remove('updating');
          jobCard.classList.add('update-success');
          setTimeout(() => {
            jobCard.classList.remove('update-success');
          }, 1000);
        }
        updateColumnCounts();
      } else {
        console.error("Failed to update job status:", data.error);
        if (jobCard) {
          jobCard.style.opacity = "1";
          jobCard.classList.remove('updating');
          jobCard.classList.add('update-error');
          setTimeout(() => {
            jobCard.classList.remove('update-error');
          }, 1000);
        }
      }
    })
    .catch((error) => {
      console.error("Error updating job status:", error);
      if (jobCard) {
        jobCard.style.opacity = "1";
        jobCard.classList.remove('updating');
      }
    });
}

function updateColumnHeader(status) {
  const column = document.getElementById(status);
  if (!column) {
    console.error(`Column not found for status: ${status}`);
    return;
  }

  const jobCards = column.querySelectorAll(".job-card");
  const countDisplay = document.querySelector(`#${status}-count`);

  if (countDisplay) {
    countDisplay.textContent = jobCards.length;
  }
}

function updateColumnCounts() {
  // Update count for each column
  document.querySelectorAll('.kanban-column').forEach(column => {
    const columnId = column.id;
    const jobList = column.querySelector('.job-list');
    const countDisplay = document.querySelector(`#${columnId}-count`);
    
    if (countDisplay && jobList) {
      const visibleCount = Array.from(jobList.children)
        .filter(child => child.style.display !== 'none').length;
      countDisplay.textContent = visibleCount;
    }
  });
}

function filterJobs() {
  const searchTerm = document.getElementById("search").value.toLowerCase();
  const alertContainer = document.getElementById("search-alert");

  if (!alertContainer) {
    const alert = document.createElement("div");
    alert.id = "search-alert";
    alert.classList.add(
      "alert",
      "alert-warning",
      "small",
      "text-muted",
      "py-1",
    );
    alert.style.opacity = "0.7";
    alert.textContent = "⚠️ Showing results from currently loaded jobs only.";
    document.querySelector(".search-container").after(alert);
  }

  document.querySelectorAll(".kanban-column").forEach((column) => {
    const jobCards = column.querySelectorAll(".job-card");
    jobCards.forEach((card) => {
      const combinedText = [
        card.dataset.jobName,
        card.dataset.jobDescription,
        card.dataset.clientName,
        card.dataset.jobNumber,
      ]
        .join(" ")
        .toLowerCase();
      card.style.display = combinedText.includes(searchTerm) ? "" : "none";
    });
  });
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
