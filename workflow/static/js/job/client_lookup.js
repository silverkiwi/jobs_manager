import { debouncedAutosave } from "./edit_job_form_autosave.js";

document.addEventListener("DOMContentLoaded", function () {
  const clientInput = document.getElementById("client_name");
  const suggestionsContainer = document.getElementById(
    "clientSuggestionsContainer",
  );

  if (!clientInput || !suggestionsContainer) {
    console.error("Client input field or suggestions container not found.");
    return;
  }

  function hideDropdown() {
    suggestionsContainer.innerHTML = "";
    suggestionsContainer.classList.add("d-none");
  }

  function showDropdown() {
    suggestionsContainer.classList.remove("d-none");
  }

  clientInput.addEventListener("input", function () {
    const query = clientInput.value.trim();

    if (query.length > 2) {
      fetch(`/api/client-search/?q=${encodeURIComponent(query)}`, {
        method: "GET",
        headers: {
          "X-CSRFToken": getCsrfToken(),
          "Content-Type": "application/json",
        },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(
              "Network response was not ok: " + response.statusText,
            );
          }
          return response.json();
        })
        .then((data) => {
          displayClientSuggestions(data.results, query);
          showDropdown();
        })
        .catch((error) => {
          console.error("Error fetching client data:", error);
          hideDropdown();
        });
    } else {
      hideDropdown();
    }
  });

  // Global click event to close the dropdown
  document.addEventListener("click", function (event) {
    const isClickInsideInput = clientInput.contains(event.target);
    const isClickInsideContainer = suggestionsContainer.contains(event.target);

    if (!isClickInsideInput && !isClickInsideContainer) {
      suggestionsContainer.innerHTML = ""; // Clear suggestions
    }
  });

  // Prevent click inside the suggestions container from propagating
  suggestionsContainer.addEventListener("click", function (event) {
    event.stopPropagation(); // Prevents global listener from triggering
  });

  function displayClientSuggestions(clients, query) {
    suggestionsContainer.innerHTML = "";

    if (clients.length === 0) {
      const noResultsItem = document.createElement("div");
      noResultsItem.classList.add("suggestion-item");
      noResultsItem.textContent = "No clients found";
      suggestionsContainer.appendChild(noResultsItem);
    } else {
      clients.forEach((client) => {
        const suggestionItem = document.createElement("div");
        suggestionItem.classList.add("suggestion-item");
        suggestionItem.textContent = client.name;
        suggestionItem.dataset.clientId = client.id;

        suggestionItem.addEventListener("click", function () {
          clientInput.value = client.name;
          const clientIdField = document.getElementById("client_id");
          const clientNameField = document.getElementById("client_name");

          clientIdField.value = client.id;
          clientNameField.value = client.name;

          if (!clientIdField.value || !clientNameField.value) {
            console.error(
              "Failed to update client_id or client_name in the form.",
            );
            renderMessages(
              [
                {
                  level: "error",
                  message:
                    "Failed to update client_id or client_name in the form.",
                },
              ],
              "job-details",
            );
          }

          debouncedAutosave();
          hideDropdown();
        });

        suggestionsContainer.appendChild(suggestionItem);
      });
    }

    const addNewOption = document.createElement("div");
    addNewOption.classList.add("suggestion-item", "add-new-client");
    addNewOption.textContent = `Add new client "${query}"`;
    addNewOption.addEventListener("click", function () {
      const newWindow = window.open(
        `/client/add/?name=${encodeURIComponent(query)}`,
        "_blank",
      );
      if (newWindow) {
        newWindow.focus();
      }

      debouncedAutosave();
      hideDropdown();
    });
    suggestionsContainer.appendChild(addNewOption);
  }

  document.addEventListener("click", function (event) {
    if (
      !clientInput.contains(event.target) &&
      !suggestionsContainer.contains(event.target)
    ) {
      hideDropdown();
    }
  });

  suggestionsContainer.addEventListener("click", function (event) {
    event.stopPropagation();
  });

  function getCsrfToken() {
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
    return csrfToken ? csrfToken.value : "";
  }
});
