// Debounce function to avoid frequent autosave calls
function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Function to collect all data from the form
function collectAllData() {
    const data = {};  // Collects main form data

    // Collect data directly from visible input fields in the form
    const formElements = document.querySelectorAll('.autosave-input');

    formElements.forEach(element => {
        let value;
        if (element.type === 'checkbox') {
            value = element.checked;
        } else {
            value = element.value.trim() === "" ? null : element.value;
        }
        data[element.name] = value;
    });

    // Add job validity check
    data.job_is_valid = checkJobValidity();

    // 2. Get all historical pricings that were passed in the initial context
    let historicalPricings = JSON.parse(JSON.stringify(window.historical_job_pricings_json));

    // 3. Collect latest revisions from AG Grid
    data.latest_estimate_pricing = collectGridData('estimate');
    data.latest_quote_pricing = collectGridData('quote');
    data.latest_reality_pricing = collectGridData('reality');

    // 4. Add the historical pricings to jobData
    data.historical_pricings = historicalPricings;

    return data;

}

function checkJobValidity() {
    // Check if all required fields are populated
    const requiredFields = ['job_name', 'client_id', 'contact_person', 'job_number'];
    const isValid = requiredFields.every(field => {
        const value = document.getElementById(field)?.value;
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
    if (Object.keys(collectedData).length === 0) {
        console.error("No data collected for autosave.");
        return;
    }
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
    .then(response => {
        if (!response.ok) {
            // If the server response is not OK, it might contain validation errors.
            return response.json().then(data => {
                if (data.errors) {
                    handleValidationErrors(data.errors);
                }
                throw new Error('Validation errors occurred');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('Autosave successful:', data);
    })
    .catch(error => {
        console.error('Autosave failed:', error);
    });
}

function handleValidationErrors(errors) {
    // Clear previous error messages
    document.querySelectorAll('.invalid-feedback').forEach(errorMsg => errorMsg.remove());
    document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

    // Display new errors
    for (const [field, messages] of Object.entries(errors)) {
        const element = document.querySelector(`[name="${field}"]`);
        if (element) {
            element.classList.add('is-invalid');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            errorDiv.innerText = messages.join(', ');
            element.parentElement.appendChild(errorDiv);

            // Attach listener to remove the error once the user modifies the field
            element.addEventListener('input', () => {
                element.classList.remove('is-invalid');
                if (element.nextElementSibling && element.nextElementSibling.classList.contains('invalid-feedback')) {
                    element.nextElementSibling.remove();
                }
            }, { once: true });
        }
    }
}

// Helper function to get CSRF token for Django
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

function removeValidationError(element) {
    element.classList.remove('is-invalid');
    if (element.nextElementSibling && element.nextElementSibling.classList.contains('invalid-feedback')) {
        element.nextElementSibling.remove();
    }
}

// Debounced version of the autosave function
const debouncedAutosave = debounce(function() {
    console.log("Debounced autosave called");
    autosaveData();
}, 1000);

const debouncedRemoveValidation = debounce(function(element) {
    console.log("Debounced validation removal called for element:", element);
    removeValidationError(element);
}, 1000);

// Attach autosave to form elements (input, select, textarea)
// Synchronize visible UI fields with hidden form fields
document.addEventListener('DOMContentLoaded', function () {
    // Synchronize all elements with the 'autosave-input' class
    const autosaveInputs = document.querySelectorAll('.autosave-input');

    // Attach change event listener to handle special input types like checkboxes
    autosaveInputs.forEach(fieldElement => {
        fieldElement.addEventListener('blur', function() {
            console.log("Blur event fired for:", fieldElement);
            debouncedRemoveValidation(fieldElement);
            debouncedAutosave();
        });

        if (fieldElement.type === 'checkbox') {
            fieldElement.addEventListener('change', function() {
                console.log("Change event fired for checkbox:", fieldElement);
                debouncedRemoveValidation(fieldElement);
                debouncedAutosave();
            });
        }

        if (fieldElement.tagName === 'SELECT') {
            fieldElement.addEventListener('change', function() {
                console.log("Change event fired for select:", fieldElement);
                debouncedRemoveValidation(fieldElement);
                debouncedAutosave();
            });
        }
    });

    // Function to validate all required fields before autosave
    // Unused?
    // function validateAllFields() {
    //     let allValid = true;
    //
    //     autosaveInputs.forEach(input => {
    //         if (input.hasAttribute('required') && input.type !== "checkbox" && input.value.trim() === '') {
    //             // Add validation error for required fields that are empty
    //             addValidationError(input, 'This field is required.');
    //             allValid = false;
    //         } else if (input.type === "checkbox" && input.hasAttribute('required') && !input.checked) {
    //             // If a checkbox is required but not checked
    //             addValidationError(input, 'This checkbox is required.');
    //             allValid = false;
    //         } else {
    //             // Remove validation error if field is valid
    //             removeValidationError(input);
    //         }
    //     });
    //
    //     return allValid;
    // }

    // // Function to add validation error to an input
    // Unused?
    // function addValidationError(element, message) {
    //     element.classList.add('is-invalid');
    //     if (!element.nextElementSibling || !element.nextElementSibling.classList.contains('invalid-feedback')) {
    //         const errorDiv = document.createElement('div');
    //         errorDiv.className = 'invalid-feedback';
    //         errorDiv.innerText = message;
    //         element.parentElement.appendChild(errorDiv);
    //     }
    // }

    // Function to remove validation error from an input
    // Unused?



});
