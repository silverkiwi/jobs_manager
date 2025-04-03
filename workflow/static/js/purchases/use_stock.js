document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const stockSearchInput = document.getElementById('stockSearchInput');
    const stockGrid = document.getElementById('stockGrid');
    const addStockBtn = document.getElementById('addStockBtn');
    
    // Modals
    const useStockModal = new bootstrap.Modal(document.getElementById('useStockModal'));
    const addStockModal = new bootstrap.Modal(document.getElementById('addStockModal'));
    const deleteStockModal = new bootstrap.Modal(document.getElementById('deleteStockModal'));
    
    // Use Stock form elements
    const stockItemIdInput = document.getElementById('stockItemId');
    const stockDescriptionInput = document.getElementById('stockDescription');
    const availableQuantityInput = document.getElementById('availableQuantity');
    const unitCostInput = document.getElementById('unitCost');
    const jobSelect = document.getElementById('jobSelect');
    const quantityUsedInput = document.getElementById('quantityUsed');
    const confirmUseStockBtn = document.getElementById('confirmUseStock');
    
    // Add Stock form elements
    const newStockDescriptionInput = document.getElementById('newStockDescription');
    const newStockQuantityInput = document.getElementById('newStockQuantity');
    const newStockUnitCostInput = document.getElementById('newStockUnitCost');
    const newStockSourceSelect = document.getElementById('newStockSource');
    const newStockNotesInput = document.getElementById('newStockNotes');
    const confirmAddStockBtn = document.getElementById('confirmAddStock');
    
    // Delete Stock form elements
    const deleteStockIdInput = document.getElementById('deleteStockId');
    const deleteStockDescriptionText = document.getElementById('deleteStockDescription');
    const confirmDeleteStockBtn = document.getElementById('confirmDeleteStock');
    
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    // Initialize AG Grid
    let stockData = [];
    
    // Fetch stock data from the JSON
    const stockDataElement = document.getElementById('stockData');
    if (stockDataElement) {
        stockData = JSON.parse(stockDataElement.textContent);
    } else {
        throw new Error('Stock data element not found');
    }
    
    // Column definitions for AG Grid
    const columnDefs = [
        { field: 'description', headerName: 'Description', flex: 2, filter: true, sortable: true },
        { field: 'quantity', headerName: 'Quantity', flex: 1, sortable: true },
        { field: 'unit_cost', headerName: 'Unit Cost', flex: 1, valueFormatter: params => `$${parseFloat(params.value).toFixed(2)}` },
        { field: 'unit_revenue', headerName: 'Unit Revenue', flex: 1, valueFormatter: params => `$${parseFloat(params.value).toFixed(2)}` },
        { field: 'total_value', headerName: 'Total Value', flex: 1, valueFormatter: params => `$${parseFloat(params.value).toFixed(2)}` },
        {
            headerName: 'Actions',
            flex: 3,
            cellRenderer: params => {
                return `
                    <div class="d-flex gap-1">
                        <button class="btn btn-primary btn-sm use-stock-btn"
                            data-stock-id="${params.data.id}"
                            data-use-all="true">
                            Use Stock
                        </button>
                        <button class="btn btn-secondary btn-sm use-partially-btn"
                            data-stock-id="${params.data.id}"
                            data-use-all="false">
                            Use Partially
                        </button>
                        <button class="btn btn-danger btn-sm delete-stock-btn"
                            data-stock-id="${params.data.id}">
                            Delete
                        </button>
                    </div>
                `;
            }
        }
    ];
    
    // AG Grid options
    const gridOptions = {
        columnDefs: columnDefs,
        rowData: stockData,
        defaultColDef: {
            flex: 1,
            minWidth: 80,
            resizable: true,
            sortable: true
        },
        rowHeight: 30, // Smaller row height for compact display
        headerHeight: 35,
        suppressCellFocus: true,
        animateRows: true,
        pagination: true,
        paginationPageSize: 100,
        domLayout: 'normal',
        rowSelection: 'single',
        rowClass: 'ag-row-compact', // Add a class for custom styling
        overlayNoRowsTemplate: '<div class="no-results">No stock items available</div>'
    };
    
    // Initialize the grid
    const grid = new agGrid.Grid(stockGrid, gridOptions);
    
    // Add event listener for the grid
    stockGrid.addEventListener('click', function(event) {
        // Check if the clicked element is a button
        const button = event.target.closest('button');
        if (!button) return;
        
        // Get the stock ID from the button's data attribute
        const stockId = button.getAttribute('data-stock-id');
        if (!stockId) return;
        
        // Find the stock item in the grid data
        let stockItem = null;
        
        // Search through all rows to find the matching stock item
        gridOptions.api.forEachNode(node => {
            if (node.data.id == stockId) {
                stockItem = node.data;
            }
        });
        
        if (!stockItem) {
            alert('Stock item not found. Please refresh the page and try again.');
            return;
        }
        
        // Handle different button types
        if (button.classList.contains('delete-stock-btn')) {
            // Populate delete modal fields
            deleteStockIdInput.value = stockItem.id;
            deleteStockDescriptionText.textContent = stockItem.description;
            
            // Show delete modal
            deleteStockModal.show();
        } else {
            // This is either use-stock-btn or use-partially-btn
            const useAll = button.classList.contains('use-stock-btn');
            
            // Populate modal fields
            stockItemIdInput.value = stockItem.id;
            stockDescriptionInput.value = stockItem.description;
            availableQuantityInput.value = stockItem.quantity;
            unitCostInput.value = stockItem.unit_cost;
            
            // Reset other form fields
            jobSelect.value = '';
            
            // Set quantity based on button clicked
            if (useAll) {
                quantityUsedInput.value = stockItem.quantity;
            } else {
                quantityUsedInput.value = '';
            }
            
            quantityUsedInput.classList.remove('is-invalid');
            
            // Set max quantity
            quantityUsedInput.max = stockItem.quantity;
            
            // Show modal
            useStockModal.show();
        }
    });
    
    // Add Stock button click handler
    addStockBtn.addEventListener('click', function() {
        // Reset form fields
        newStockDescriptionInput.value = '';
        newStockQuantityInput.value = '';
        newStockUnitCostInput.value = '';
        newStockSourceSelect.value = '';
        newStockNotesInput.value = '';
        
        // Show modal
        addStockModal.show();
    });
    
    // Search functionality
    stockSearchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase().trim();
        gridOptions.api.setQuickFilter(searchTerm);
    });
    
    // Validate quantity input
    quantityUsedInput.addEventListener('input', function() {
        validateQuantity();
    });
    
    function validateQuantity() {
        const quantityUsed = parseFloat(quantityUsedInput.value || 0);
        const maxQuantity = parseFloat(quantityUsedInput.max || 0);
        let isValid = true;
        
        if (quantityUsed <= 0 || quantityUsed > maxQuantity) {
            quantityUsedInput.classList.add('is-invalid');
            isValid = false;
        } else {
            quantityUsedInput.classList.remove('is-invalid');
        }
        
        confirmUseStockBtn.disabled = !isValid || !jobSelect.value;
        return isValid;
    }
    
    // Enable/disable confirm button based on job selection
    jobSelect.addEventListener('change', function() {
        confirmUseStockBtn.disabled = !this.value || !validateQuantity();
    });
    
    // Handle form submission
    confirmUseStockBtn.addEventListener('click', async function() {
        // Validate form
        if (!jobSelect.value || !validateQuantity()) {
            return;
        }
        
        // Disable button and show loading state
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        
        // Prepare data for API call
        const consumeData = {
            job_id: jobSelect.value,
            stock_item_id: stockItemIdInput.value,
            quantity_used: parseFloat(quantityUsedInput.value)
        };
        
        try {
            // Make API call
            const response = await fetch('/api/stock/consume/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken || document.querySelector('input[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify(consumeData)
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // Close modal
                useStockModal.hide();
                
                // Show success message
                alert(result.message || 'Stock consumed successfully!');
                
                // Reload page to refresh stock list
                window.location.reload();
            } else {
                const errorData = await response.json();
                alert(`Error: ${errorData.error || 'Failed to consume stock.'}`);
            }
        } catch (error) {
            console.error('Error consuming stock:', error);
            alert('An unexpected error occurred while consuming stock.');
        } finally {
            // Reset button state
            this.disabled = false;
            this.innerHTML = 'Confirm';
        }
    });
    
    // Handle Add Stock form submission
    confirmAddStockBtn.addEventListener('click', async function() {
        // Validate form
        const form = document.getElementById('addStockForm');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        // Disable button and show loading state
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        
        // Prepare data for API call
        const stockData = {
            description: newStockDescriptionInput.value,
            quantity: parseFloat(newStockQuantityInput.value),
            unit_cost: parseFloat(newStockUnitCostInput.value),
            source: newStockSourceSelect.value,
            notes: newStockNotesInput.value
        };
        
        try {
            // Make API call
            const response = await fetch('/api/stock/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken || document.querySelector('input[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify(stockData)
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // Close modal
                addStockModal.hide();
                
                // Show success message
                alert(result.message || 'Stock item created successfully!');
                
                // Reload page to refresh stock list
                window.location.reload();
            } else {
                const errorData = await response.json();
                alert(`Error: ${errorData.error || 'Failed to create stock item.'}`);
            }
        } catch (error) {
            console.error('Error creating stock item:', error);
            alert('An unexpected error occurred while creating stock item.');
        } finally {
            // Reset button state
            this.disabled = false;
            this.innerHTML = 'Add Stock';
        }
    });
    
    // Handle Delete Stock form submission
    confirmDeleteStockBtn.addEventListener('click', async function() {
        // Disable button and show loading state
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        
        // Prepare data for API call
        const stockId = deleteStockIdInput.value;
        
        try {
            // Make API call
            const response = await fetch(`/api/stock/${stockId}/deactivate/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken || document.querySelector('input[name=csrfmiddlewaretoken]').value
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // Close modal
                deleteStockModal.hide();
                
                // Show success message
                alert(result.message || 'Stock item deleted successfully!');
                
                // Reload page to refresh stock list
                window.location.reload();
            } else {
                const errorData = await response.json();
                alert(`Error: ${errorData.error || 'Failed to delete stock item.'}`);
            }
        } catch (error) {
            console.error('Error deleting stock item:', error);
            alert('An unexpected error occurred while deleting stock item.');
        } finally {
            // Reset button state
            this.disabled = false;
            this.innerHTML = 'Delete';
        }
    });
});