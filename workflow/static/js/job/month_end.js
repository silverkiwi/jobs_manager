document.addEventListener('DOMContentLoaded', function() {
  const jobCheckboxes = document.querySelectorAll('.job-checkbox');
  const processButton = document.getElementById('processButton');
  const selectAllButton = document.getElementById('selectAll');
  const deselectAllButton = document.getElementById('deselectAll');
  const selectAllCheckbox = document.getElementById('selectAllCheckbox');
  
  // Update process button state based on selections
  function updateProcessButtonState() {
    const anyChecked = Array.from(jobCheckboxes).some(cb => cb.checked);
    processButton.disabled = !anyChecked;
  }
  
  // Select/deselect all checkboxes
  function updateAllCheckboxes(checked) {
    jobCheckboxes.forEach(checkbox => {
      checkbox.checked = checked;
    });
    updateProcessButtonState();
  }
  
  // Update header checkbox state
  function updateHeaderCheckbox() {
    const checkedCount = Array.from(jobCheckboxes).filter(cb => cb.checked).length;
    
    if (checkedCount === 0) {
      selectAllCheckbox.checked = false;
      selectAllCheckbox.indeterminate = false;
    } else if (checkedCount === jobCheckboxes.length) {
      selectAllCheckbox.checked = true;
      selectAllCheckbox.indeterminate = false;
    } else {
      selectAllCheckbox.indeterminate = true;
    }
  }
  
  // Add event listeners to each checkbox
  jobCheckboxes.forEach(checkbox => {
    checkbox.addEventListener('change', function() {
      updateProcessButtonState();
      updateHeaderCheckbox();
    });
  });
  
  // Header checkbox event
  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener('change', function() {
      updateAllCheckboxes(this.checked);
    });
  }
  
  // Select all button
  if (selectAllButton) {
    selectAllButton.addEventListener('click', function() {
      updateAllCheckboxes(true);
      updateHeaderCheckbox();
    });
  }
  
  // Deselect all button
  if (deselectAllButton) {
    deselectAllButton.addEventListener('click', function() {
      updateAllCheckboxes(false);
      updateHeaderCheckbox();
    });
  }
  
  // Add row click handler to toggle checkboxes
  const tableRows = document.querySelectorAll('tbody tr');
  tableRows.forEach(row => {
    row.addEventListener('click', function(e) {
      // Only handle if the click wasn't on a checkbox itself
      if (e.target.type !== 'checkbox') {
        const checkbox = this.querySelector('.job-checkbox');
        checkbox.checked = !checkbox.checked;
        
        // Trigger the change event
        const event = new Event('change');
        checkbox.dispatchEvent(event);
      }
    });
  });
}); 