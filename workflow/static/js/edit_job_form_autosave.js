// Debounce function to avoid frequent autosave calls
function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Function to collect data from grids and form fields
function collectAllData() {
    const sections = ['estimate', 'quote', 'reality'];
    const grids = ['TimeTable', 'MaterialsTable', 'AdjustmentsTable'];
    const data = {};

    // Collect grid data from all sections
    sections.forEach(section => {
        data[section] = {};
        grids.forEach(gridName => {
            const gridElement = document.querySelector(`#${section}${gridName}`);
            if (gridElement) {
                const gridOptions = gridElement.__agGridOptions__;
                if (gridOptions && gridOptions.api) {
                    data[section][gridName.toLowerCase().replace('table', '')] = gridOptions.api.getAllRows();
                } else {
                    console.error(`Grid API not found for ${section}${gridName}`);
                }
            }
        });
    });

    // Collect data from all form fields (inputs, selects, textareas)
    const formElements = document.querySelectorAll('input, select, textarea');
    formElements.forEach(element => {
        if (element.name || element.id) {
            data[element.name || element.id] = element.value;
        }
    });

    return data;
}

// Autosave function to send data to the server
function autosaveData() {
    const collectedData = collectAllData();
    saveDataToServer(collectedData);
}

// Function to make POST request to the API endpoint
function saveDataToServer(collectedData) {
    console.log('Autosaving data to /api/autosave-job/...', collectedData);

    fetch('/api/autosave-job/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(collectedData)
    })
        .then(response => response.json())
        .then(data => {
            console.log('Autosave successful:', data);
        })
        .catch(error => {
            console.error('Autosave failed:', error);
        });
}

// Helper function to get CSRF token for Django
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// Debounced version of the autosave function
const debouncedAutosaveData = debounce(autosaveData, 500);

// Attach autosave to form elements (input, select, textarea)
document.addEventListener('DOMContentLoaded', function () {
    const formElements = document.querySelectorAll('input, select, textarea');
    formElements.forEach(element => {
        if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
            element.addEventListener('input', debouncedAutosaveData);
        } else if (element.tagName === 'SELECT') {
            element.addEventListener('change', debouncedAutosaveData);
        }
    });
});
