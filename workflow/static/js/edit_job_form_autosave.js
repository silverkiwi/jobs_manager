// Debounce function to avoid frequent autosave calls
function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function collectAllData() {
    const sections = ['estimate', 'quote', 'reality'];
    const grids = ['TimeTable', 'MaterialsTable', 'AdjustmentsTable'];
    const data = {};

    // Initialize AG Grids for Time, Materials, and Adjustments tables
    sections.forEach(section => {
        data[section] = {};
        grids.forEach(gridName => {
            const gridInstance = window.grids[`${section}${gridName}`];

            if (gridInstance) {
                console.log(`Grid instance is defined for ${section}${gridName}`);
            } else {
                console.error(`Grid instance NOT found for ${section}${gridName}`);
                return;  // If the grid instance is not found, skip this grid
            }

            if (gridInstance.gridApi) {
                console.log(`Collecting data for ${section}${gridName}`);

                // Use the forEachNode method to collect row data
                const rowData = [];
                gridInstance.gridApi.forEachNode(node => rowData.push(node.data));

                // Store the row data in the data object
                data[section][gridName.toLowerCase().replace('table', '')] = rowData;

                console.log(`Collected ${rowData.length} rows for ${section}${gridName}`);
            } else {
                console.error(`Grid API not found for ${section}${gridName}`);
            }
        });
    });

    // Collect data from all form fields (inputs, selects, textareas)
    const formElements = document.querySelectorAll('input, select, textarea');
    formElements.forEach(element => {
        if (element.name || element.id) {
            data[element.name || element.id] = element.value;
            console.log(`Collected form element data: ${element.name || element.id} = ${element.value}`);
        }
    });

    console.log('All data collected:', data);
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
