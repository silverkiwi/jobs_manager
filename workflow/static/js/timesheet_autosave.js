// Debounce function to reduce frequent server calls
function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function collectGridData() {
    console.log('collectGridData() called');
    const gridData = [];

    // Instead of looking for grid on the element, use the window.grid we stored
    const grid = window.grid;
    console.log('Grid instance:', grid);

    if (!grid) {
        console.error('Could not get grid instance');
        return gridData;
    }

    grid.forEachNode(node => {
        console.log('Processing node:', node);
        if (data.job_number && (data.hours > 0 || (data.description && data.description.trim() !== ''))) {
            console.log('Adding valid row:', data);
            gridData.push(data);
        } else {
            console.log('Skipping dummy or invalid row:', data);
        }
    });

    console.log('Final collected data:', gridData);
    return gridData;
}

// Autosave function
function autosaveData() {
    const collectedData = collectGridData();
    if (!collectedData.length) {
        console.error("No timesheet data available for autosave.");
        return;
    }
    saveDataToServer({ time_entries: collectedData });
}

// Send data to the server
function saveDataToServer(collectedData) {
    console.log('Autosaving timesheet data to /api/autosave-timesheet/...', collectedData);

    fetch('/api/autosave-timesheet/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(collectedData)
    })
    .then(response => {
        if (!response.ok) {
            console.error('Server responded with an error:', response.status);
            return;
        }
        console.log('Autosave successful');
    })
    .catch(error => {
        console.error('Autosave failed:', error);
    });
}

// Get CSRF token for Django
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// Debounced autosave function
const debouncedAutosave = debounce(autosaveData, 1000);

// Removed.  We debounce explicitly from the grid
// // Attach autosave to grid events
// document.addEventListener('DOMContentLoaded', () => {
//     window.gridOptions.api.addEventListener('cellValueChanged', () => {
//         console.log('Grid value changed, triggering debounced autosave.');
//         debouncedAutosave();
//     });
// });
