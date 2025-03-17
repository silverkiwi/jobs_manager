import { setupAdvancedSearch } from "./job/advanced_search.js";

console.log("kanban.js load started");

let currentSearchTerm = '';

document.addEventListener("DOMContentLoaded", function () {
  console.log("Script loaded and DOM fully loaded");

  initializeColumns();
  setupToggleArchived();
  setupAdvancedSearch();

  document.getElementById("search").addEventListener("input", function() {
    filterJobs();
    updateColumnCounts();
  });
});

function initializeColumns() {
  const columns = document.querySelectorAll(".kanban-column");
  const columnIds = Array.from(columns).map(col => col.id);

  columnIds.forEach(status => {
    loadJobs(status);
  });

  initializeDragAndDrop();
}

function loadJobs(status) {
  const container = document.querySelector(`#${status} .job-list`);

  container.innerHTML = `
    <div class="loading-indicator">
      <i class="bi bi-hourglass-split"></i> Loading...
    </div>
  `;

  let url = `/kanban/fetch_jobs/${status}/`;
  if (currentSearchTerm) {
    url += `?search=${encodeURIComponent(currentSearchTerm)}`;
  }

  fetch(url)
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        renderJobs(status, data.jobs);
        updateCounters(status, data.filtered_count, data.total);
        const loadMoreContainer = document.querySelector(`#${status}-load-more-container`);
        if (loadMoreContainer) {
          loadMoreContainer.remove()
        } 
      } else {
        console.error(`Error loading ${status} jobs:`, data.error);
        container.innerHTML = `
          <div class="error-message"> Error: ${data.error}</div>
        `;
      }
    })
    .catch(error => {
      console.error(`Error loading ${status} jobs:`, error);
      container.innerHTML = '<div class="error-message"> Error loading jobs. Please try againg.</div>';
    });
}

function refreshAllColumns() {
  const columns = document.querySelectorAll('.kanban-column');
  const columnIds = Array.from(columns).map(col => col.id);

  columnIds.forEach(status => {
    loadJobs(status);
  })
}

function renderJobs(status, jobs) {
  const container = document.querySelector(`#${status} .job-list`);
  container.innerHTML = '';

  if (jobs.length === 0) {
    container.innerHTML = `
      <div class="empty-message">No jobs found</div>
    `;
    return;
  }

  jobs.forEach(job => {
    const jobCard = createJobCard(job);
    container.appendChild(jobCard);
  });
}

function updateCounters(status, filteredCount, totalCount) {
  const countElement = document.getElementById(`${status}-count`);
  const totalElement = document.getElementById(`${status}-total`);

  if (countElement) countElement.textContent = filteredCount;
  if (totalElement) totalElement.textContent = totalCount;
}

function fetchStatusValues() {
  fetch("/api/fetch_status_values/")
    .then((response) => response.json())
    .then((statuses) => {
      Object.keys(statuses).forEach((status) => {
        loadJobs(status, true);
      });

      // After loading statuses, initialize drag and drop functionality
      initializeDragAndDrop();
    })
    .catch((error) => console.error("Error fetching status values:", error));
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
    <a href="/job/${job.id}/">
      <div class="job-card-title">${job.job_number}</div>
      <div class="job-card-body small">
        ${job.name}
      </div>
    </a>
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

        // Remove potential destiny class
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

function updateJobStatus(jobId, newStatus) {
  fetch(`/jobs/${jobId}/update_status/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: JSON.stringify({
      status: newStatus
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      // Atualizar contadores
      refreshAllColumns();
    } else {
      alert('Failed to update job status: ' + data.error);
      // Recarregar para restaurar o estado
      refreshAllColumns();
    }
  })
  .catch(error => {
    console.error('Error updating job status:', error);
    alert('Failed to update job status. Please try again.');
    refreshAllColumns();
  });
}

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

function setupToggleArchived() {
  const toggleButton = document.getElementById("toggleArchive");
  const archiveContainer = document.getElementById("archiveContainer");

  let archivedVisible = false;

  loadJobs("archived");

  toggleButton.addEventListener("click", () => {
    archivedVisible = !archivedVisible;

    switch (archivedVisible) {
      case true:
        archiveContainer.style.display = "grid";
        this.querySelector("i").className = "bi bi-chevron-up";
        loadJobs("archived");
        break;
      default:
        archiveContainer.style.display = "none";
        this.querySelector("i").className = "bi bi-chevron-down";
        break;
    }
  });
}
