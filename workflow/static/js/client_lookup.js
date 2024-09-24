document.addEventListener('DOMContentLoaded', function () {
    const clientInput = document.getElementById('clientName');
    const suggestionsContainer = document.getElementById('clientSuggestionsContainer');

    clientInput.addEventListener('input', function () {
        const query = clientInput.value;
        console.log("Client query event triggered: ", query);  //

        // Only search when there's a query longer than 2 characters
        if (query.length > 2) {
            fetch(`/api/client-search/?q=${query}`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                displayClientSuggestions(data, query);
            })
            .catch(error => {
                console.error('Error fetching client data:', error);
            });
        } else {
            suggestionsContainer.innerHTML = ''; // Clear suggestions if the query is too short
        }
    });

    function displayClientSuggestions(clients, query) {
        suggestionsContainer.innerHTML = ''; // Clear previous suggestions

        clients.forEach(client => {
            const suggestionItem = document.createElement('div');
            suggestionItem.classList.add('suggestion-item');
            suggestionItem.textContent = client.name;
            suggestionItem.dataset.clientId = client.id;
            suggestionItem.addEventListener('click', function () {
                clientInput.value = client.name;
                suggestionsContainer.innerHTML = ''; // Clear suggestions after selecting
            });
            suggestionsContainer.appendChild(suggestionItem);
        });

        // Add 'Add new client' option at the end of the list
        const addNewOption = document.createElement('div');
        addNewOption.classList.add('suggestion-item', 'add-new-client');
        addNewOption.textContent = `Add new client "${query}"`;
        addNewOption.addEventListener('click', function () {
            // Redirect or trigger modal to add a new client
            window.location.href = `/clients/add/?name=${query}`;
        });
        suggestionsContainer.appendChild(addNewOption);
    }

    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }
});
