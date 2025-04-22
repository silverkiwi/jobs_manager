/**
 * Utility functions for working with enums in the frontend
 */

/**
 * Fetches enum choices from the API
 * @param {string} enumName - The name of the enum to fetch (e.g., 'MetalType')
 * @returns {Promise<Array>} - A promise that resolves to an array of {value, display_name} objects
 */
async function fetchEnumChoices(enumName) {
    try {
        const response = await fetch(`/api/enums/${enumName}/`);
        
        if (!response.ok) {
            const errorData = await response.json();
            console.error(`Error fetching enum ${enumName}:`, errorData);
            throw new Error(errorData.error || `Failed to fetch enum ${enumName}`);
        }
        
        const data = await response.json();
        return data.choices;
    } catch (error) {
        console.error(`Error fetching enum ${enumName}:`, error);
        throw error;
    }
}

/**
 * Populates a select element with options from an enum
 * @param {HTMLSelectElement|string} selectElement - The select element or its ID
 * @param {string} enumName - The name of the enum to fetch
 * @param {string} [defaultValue] - Optional default value to select
 * @returns {Promise<void>}
 */
async function populateSelectWithEnum(selectElement, enumName, defaultValue = null) {
    // Get the select element if a string ID was provided
    if (typeof selectElement === 'string') {
        selectElement = document.getElementById(selectElement);
    }
    
    if (!selectElement) {
        console.error(`Select element not found for enum ${enumName}`);
        return;
    }
    
    try {
        // Clear existing options except the first one (if it's a placeholder)
        const firstOption = selectElement.options[0];
        selectElement.innerHTML = '';
        
        if (firstOption && (firstOption.disabled || firstOption.value === '')) {
            selectElement.appendChild(firstOption);
        }
        
        // Fetch enum choices
        const choices = await fetchEnumChoices(enumName);
        
        // Add options to the select element
        choices.forEach(choice => {
            const option = document.createElement('option');
            option.value = choice.value;
            option.textContent = choice.display_name;
            
            if (defaultValue && choice.value === defaultValue) {
                option.selected = true;
            }
            
            selectElement.appendChild(option);
        });
    } catch (error) {
        console.error(`Failed to populate select with enum ${enumName}:`, error);
    }
}

// Export the functions for use in other modules
export { fetchEnumChoices, populateSelectWithEnum };