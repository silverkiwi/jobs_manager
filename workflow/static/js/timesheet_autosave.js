let deletedEntries = [];

function markEntryAsDeleted(entryId) {
    if (entryId) {
        console.log('Adding entry to deletion list:', entryId);
        deletedEntries.push(entryId);
        console.log('Current deletion list:', deletedEntries);
    }
}

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
    const grid = window.grid;

    if (!grid) {
        console.error('Could not get grid instance');
        return gridData;
    }

    grid.forEachNode(node => {
        if (!node || !node.data) {
            console.log('Skipping invalid node');
            return;
        }

        console.log('Processing node:', node);

        const rowData = node.data; 

        const isValidRow = rowData.hours > 0 &&
            (rowData.description?.trim() !== '' || rowData.notes?.trim() !== '');

        if (!isValidRow) {
            console.log('Skipping invalid row:', rowData);
            return;
        }

        const previousRowData = rowStateTracker[node.id] || {};
        const rowChanged = hasRowChanged(previousRowData, rowData);

        if (!rowChanged) {
            console.log('Skipping unchanged row:', rowData);
            return;
        }

        if (rowData.id == null) {
            rowData.id = 'tempId'; 
        }
    
        const entry = {
            id: rowData.id,
            staff_id: rowData.staff_id,
            job_number: rowData.job_number,
            description: rowData.description,
            hours: rowData.hours,
            mins_per_item: rowData.mins_per_item,
            items: rowData.items,
            wage_amount: rowData.wage_amount,
            charge_out_rate: rowData.job_data.charge_out_rate,
            timesheet_date: window.timesheet_data.timesheet_date,
            bill_amount: rowData.bill_amount,
            date: rowData.date,
            job_data: rowData.job_data,
            is_billable: rowData.is_billable || true,
            notes: rowData.notes || '',
            rate_type: rowData.rate_type || 'ORDINARY'
        };

        rowStateTracker[node.id] = { ...rowData };
        console.log('Updated row state:', rowStateTracker[node.id]);

        gridData.push(entry);
    });

    console.log('Final collected data:', gridData);
    return {time_entries: gridData, deleted_entries: deletedEntries};
}

function autosaveData() {
    const collectedData = collectGridData();
    
    collectedData.time_entries = collectedData.time_entries.filter(entry => entry.id || entry.job_number);

    // Changed validation - proceed if either we have entries to update or delete
    if (collectedData.time_entries.length === 0 && collectedData.deleted_entries.length === 0) {
        console.log("No data to save - no time entries or deletions");
        return;
    }

    console.log('Saving data:', {
        timeEntries: collectedData.time_entries.length,
        deletedEntries: collectedData.deleted_entries.length
    });

    saveDataToServer(collectedData);
}

// Send data to the server
function saveDataToServer(collectedData) {
    console.log('Autosaving timesheet data to /api/autosave-timesheet/...', {
        time_entries: collectedData.time_entries.length,
        deleted_entries: collectedData.deleted_entries.length
    });

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
            return response.json().then(data => {
                console.error('Error details:', data);
                throw new Error(data.error || 'Server error');
            });
        }
        console.log('Autosave successful');
        deletedEntries = [];
        return response.json();
    })
    .then(data => {
        if (data.messages) {
            renderMessages(data.messages); // Render dynamic messages
        }

        
        console.log('Autosave successful:', data);
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
