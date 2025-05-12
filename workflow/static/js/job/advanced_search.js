import { Environment } from "../env.js";

export function setupAdvancedSearch() {
  loadClientsDropdown();
  loadStaffDropdown();

  document
    .getElementById("advancedSearchButton")
    .addEventListener("click", function () {
      const advancedSearchContainer = document.getElementById(
        "advancedSearchContainer",
      );
      advancedSearchContainer.style.display =
        advancedSearchContainer.style.display === "none" ? "block" : "none";
    });

  document
    .getElementById("closeAdvancedSearch")
    .addEventListener("click", function () {
      document.getElementById("advancedSearchContainer").style.display = "none";
    });

  document
    .getElementById("backToKanban")
    .addEventListener("click", function () {
      document.getElementById("searchResultsContainer").style.display = "none";
      document.getElementById("kanbanContainer").style.display = "block";
    });

  document
    .getElementById("advancedSearchForm")
    .addEventListener("submit", function (e) {
      e.preventDefault();
      executeAdvancedSearch();
    });

  document
    .getElementById("advancedSearchButton")
    .addEventListener("reset", function () {
      setTimeout(() => {
        document.getElementById("searchResultsContainer").style.display =
          "none";
        document.getElementById("advancedSearchContainer").style.display =
          "none";
        document.getElementById("kanbanContainer").style.display = "block";
      }, 100);
    });
}

function loadClientsDropdown() {
  if (Environment.isDebugMode()) console.log("Loading clients for dropdown...");
  fetch("/api/clients/all")
    .then((response) => {
      if (Environment.isDebugMode())
        console.log("Clients API response status:", response.status);
      return response.json().then((data) => ({ data, ok: response.ok }));
    })
    .then(({ data, ok }) => {
      if (!ok || !Array.isArray(data)) {
        console.log("Failed to load clients:", data);
        return;
      }

      if (Environment.isDebugMode())
        console.log("Clients loaded successfully:", data);
      const clientSelect = document.getElementById("advClient");
      data.forEach((client) => {
        const option = document.createElement("option");
        option.value = client.name;
        option.textContent = client.name;
        clientSelect.appendChild(option);
      });
    })
    .catch((error) => {
      console.error("Error loading clients:", error);
      if (Environment.isDebugMode())
        console.log("Client loading error details:", error);
    });
}

function loadStaffDropdown() {
  if (Environment.isDebugMode()) console.log("Loading staff for dropdown...");
  fetch("/accounts/api/staff/all", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      "X-Actual-Users": "True",
    },
  })
    .then((response) => {
      if (Environment.isDebugMode())
        console.log("Staff API response status:", response.status);
      return response.json().then((data) => ({ data, ok: response.ok }));
    })
    .then(({ data, ok }) => {
      if (!ok || !Array.isArray(data)) {
        console.log("Failed to load staff:", data);
        return;
      }
      if (Environment.isDebugMode())
        console.log("Staff loaded successfully:", data);

      const userSelect = document.getElementById("advCreatedBy");
      data.forEach((s) => {
        const option = document.createElement("option");
        option.value = s.id;
        option.textContent = `${s.first_name} ${s.last_name}`;
        userSelect.appendChild(option);
      });
    })
    .catch((error) => {
      console.error("Error loading staff:", error);
      if (Environment.isDebugMode())
        console.log("Staff loading error details:", error);
    });
}

function executeAdvancedSearch() {
  const resultsContainer = document.getElementById("searchResults");
  resultsContainer.innerHTML = `
        <div class="text-center p-5">
            <div class="spinner-border text-primary" role="status"></div>
            <p class="mt-3">Searching jobs...</p>
        </div>
    `;

  document.getElementById("searchResultsContainer").style.display = "block";
  document.getElementById("kanbanContainer").style.display = "none";

  const form = document.getElementById("advancedSearchForm");
  const formData = new FormData(form);
  const queryParams = new URLSearchParams();

  for (const [key, value] of formData.entries()) {
    // Handle status field with multiple select separately
    if (key === "status" && form.status.multiple) {
      const selectedOptions = Array.from(form.status.selectedOptions);
      selectedOptions.forEach((option) => {
        queryParams.append("status", option.value);
      });
      continue;
    }

    // Skip empty values
    if (!value) continue;

    // Add any non-empty value to query params
    queryParams.append(key, value);
  }

  if (Environment.isDebugMode())
    console.log("Query params:", queryParams.toString());
  fetch(`/api/job/advanced-search/?${queryParams.toString()}`)
    .then((response) => response.json())
    .then((data) => {
      if (!data.success) {
        resultsContainer.innerHTML = `
                <div class="alert alert-danger"> Error: ${data.error}</div>
            `;
        return;
      }
      renderSearchResults(data.jobs, data.total);
    })
    .catch((error) => {
      console.error("Error performing advanced search", error);
      resultsContainer.innerHTML = `
            <div class="alert alert-danger"> Error: ${error}</div>`;
    });
}

function renderSearchResults(jobs, total) {
  const resultsContainer = document.getElementById("searchResults");
  const resultCount = document.getElementById("result-count");

  resultCount.textContent = total;

  resultsContainer.innerHTML = "";

  if (jobs.length === 0) {
    resultsContainer.innerHTML = `
            <div class="alert alert-info">No jobs found matching your search criteria.</div>
        `;
    return;
  }

  jobs.forEach((job) => {
    const jobCard = createSearchResultCard(job);
    resultsContainer.appendChild(jobCard);
  });
}

function createSearchResultCard(job) {
  const card = document.createElement("div");
  card.classList = "job-card job-card-result";

  let statusClass = job.status_key || getStatusClassFromLabel(job.status);

  card.innerHTML = `
    <div class="d-flex align-items-center mb-2">
      <span class="job-number fw-bold">#${job.job_number}</span>
      <span class="status-badge ${statusClass}">${job.status}</span>
      ${job.paid ? '<span class="ms-2 text-success"><i class="bi bi-check-circle-fill"></i></span>' : ""}
    </div>
    <h4 class="job-title">${job.name}</h4>
    <p class="job-description small text-muted">${job.description || "No description"}</p>
    ${job.client_name ? `<div class="small mb-1"><i class="bi bi-building me-1"></i>${job.client_name}</div>` : ""}
    ${job.contact_person ? `<div class="small mb-1"><i class="bi bi-person me-1"></i>${job.contact_person}</div>` : ""}
    <div class="job-meta">
      <span><i class="bi bi-person-badge me-1"></i>${job.created_by || "Unknown"}</span>
      <span><i class="bi bi-calendar me-1"></i>${job.created_at || "Unknown date"}</span>
    </div>
    <div class="mt-2">
      <a href="/job/${job.id}/" class="btn btn-sm btn-outline-primary">
        <i class="bi bi-pencil me-1"></i>Edit
      </a>
    </div>
    `;

  return card;
}

function getStatusClassFromLabel(statusLabel) {
  const statusMap = {
    Quoting: "quoting",
    "Accepted Quote": "accepted_quote",
    Rejected: "rejected",
    "In Progress": "in_progress",
    "On Hold": "on_hold",
    Special: "special",
    Completed: "completed",
    Archived: "archived",
  };

  return statusMap[statusLabel] || "quoting";
}
