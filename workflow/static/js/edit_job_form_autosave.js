// Debounce function to avoid frequent autosave calls
function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}


function collectAllData() {
    const data = {
        id: document.getElementById('job_id').value,
        name: document.getElementById('job_name').value,
        client: document.getElementById('client_id').value,
        order_number: document.getElementById('order_number').value,
        contact_person: document.getElementById('contact_person').value,
        contact_phone: document.getElementById('phoneContact').value,
        job_number: parseInt(document.getElementById('job_number').value, 10),
        description: document.getElementById('description').value,
        date_created: document.getElementById('date_created').value,
        status: document.getElementById('jobStatus').value,
        paid: document.getElementById('paidCheckbox').checked,
        job_is_valid: checkJobValidity(), // We are responsible for calculating this

        estimate: collectGridData('estimate'),
        quote: collectGridData('quote'),
        reality: collectGridData('reality')
    };

    return data;
}

function checkJobValidity() {
    // Check if all required fields are populated
    const requiredFields = ['job_name', 'client_id', 'contact_person', 'phoneContact', 'job_number'];
    const isValid = requiredFields.every(field => {
        const value = document.getElementById(field).value;
        return value !== null && value !== undefined && value.trim() !== '';
    });

    return isValid;
}

function collectGridData(section) {
    const grids = ['TimeTable', 'MaterialsTable', 'AdjustmentsTable'];
    const sectionData = {};

    grids.forEach(gridName => {
        const gridKey = `${section}${gridName}`;
        const gridData = window.grids[gridKey];

        if (gridData && gridData.api) {
            const rowData = [];
            gridData.api.forEachNode(node => rowData.push(node.data));
            sectionData[gridName.toLowerCase().replace('table', '')] = rowData;
        } else {
            console.error(`Grid or API not found for ${gridKey}`);
        }
    });

    return sectionData;
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

