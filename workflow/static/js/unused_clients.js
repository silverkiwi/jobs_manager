document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('deleteForm');
    const deleteButton = document.getElementById('deleteButton');
    const selectAllCheckbox = document.getElementById('selectAll');
    const clientCheckboxes = document.querySelectorAll('.client-checkbox');
    const selectedCountSpan = document.getElementById('selectedCount');
    const totalCountElement = document.querySelector('.text-muted');

    function updateSelectedCount() {
        const selectedCount = document.querySelectorAll('.client-checkbox:checked').length;
        selectedCountSpan.textContent = selectedCount;
        deleteButton.disabled = selectedCount === 0;
    }

    function updateTotalCount(deletedCount) {
        const currentTotal = parseInt(totalCountElement.textContent.match(/\d+/)[0]);
        const newTotal = currentTotal - deletedCount;
        totalCountElement.textContent = `Total unused clients: ${newTotal}`;
    }

    selectAllCheckbox.addEventListener('change', function() {
        clientCheckboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
        });
        updateSelectedCount();
    });

    clientCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateSelectedCount();
            selectAllCheckbox.checked = [...clientCheckboxes].every(cb => cb.checked);
        });
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        if (!confirm('Are you sure you want to delete the selected clients? This action cannot be undone.')) {
            return;
        }

        const formData = new FormData(form);
        const selectedCheckboxes = document.querySelectorAll('.client-checkbox:checked');

        fetch('', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': formData.get('csrfmiddlewaretoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove deleted rows from the table
                selectedCheckboxes.forEach(checkbox => {
                    checkbox.closest('tr').remove();
                });
                
                // Update counts
                updateTotalCount(data.deleted_count);
                updateSelectedCount();
                
                // Reset select all checkbox
                selectAllCheckbox.checked = false;
                
                // Show success message
                alert(data.message);
                
                // If no clients left on current page and there are other pages,
                // reload to show the next page
                if (document.querySelectorAll('.client-checkbox').length === 0 && 
                    document.querySelector('.pagination')) {
                    location.reload();
                }
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            alert('Error: ' + error);
        });
    });
}); 