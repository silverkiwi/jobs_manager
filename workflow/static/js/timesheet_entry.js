class ActiveJobCellEditor {
    init(params) {
        this.value = params.value;
        this.params = params;
        this.jobs = window.timesheet_data.jobs;  // These are already filtered to open jobs

        this.div = document.createElement('div');
        this.div.className = 'job-search-container';

        this.input = document.createElement('input');
        this.input.type = 'text';
        this.input.className = 'job-search-input';
        this.input.placeholder = 'Search open jobs...';

        // Automatically focus the input field when editor is opened
        setTimeout(() => this.input.focus(), 0);

        this.listDiv = document.createElement('div');
        this.listDiv.className = 'job-list';

        // Populate list with open jobs
        this.jobs.forEach(job => {
            const jobRow = document.createElement('div');
            jobRow.className = 'job-row';
            jobRow.textContent = job.job_display_name;
            jobRow.onclick = () => this.selectJob(job);
            this.listDiv.appendChild(jobRow);
        });

        // Filter as user types
        this.input.addEventListener('input', () => {
            const searchTerm = this.input.value.trim().toLowerCase();
            this.listDiv.innerHTML = ''; // Clear previous results

            const filteredJobs = this.jobs
                .filter(job => job.job_display_name.toLowerCase().includes(searchTerm))
                .slice(0, 10); // Limit results to avoid overwhelming the user

            filteredJobs.forEach(job => {
                const jobRow = document.createElement('div');
                jobRow.className = 'job-row';
                jobRow.textContent = job.job_display_name;
                jobRow.onclick = () => this.selectJob(job);
                this.listDiv.appendChild(jobRow);
            });

            // If only one job matches, select it when pressing Enter
            if (filteredJobs.length === 1) {
                this.input.addEventListener('keydown', (event) => {
                    if (event.key === 'Enter' || event.key === 'Tab') {
                        event.stopPropagation();
                        this.selectJob(filteredJobs[0]);
                    }
                });
            }
        });

        this.div.appendChild(this.input);
        this.div.appendChild(this.listDiv);
    }

    selectJob(job) {
        this.value = job.job_number;
        this.params.stopEditing();
    }

    getGui() {
        return this.div;
    }

    getValue() {
        return this.value;
    }

    // Required AG Grid lifecycle methods
    destroy() {
    }

    isPopup() {
        return true;
    }
}

window.timesheet_data = {
    timesheet_date: JSON.parse(document.getElementById('timesheet-date').textContent),
    jobs: JSON.parse(document.getElementById('jobs-data').textContent),
    time_entries: JSON.parse(document.getElementById('timesheet-entries-data').textContent),
    staff: JSON.parse(document.getElementById('staff-data').textContent)
};

function currencyFormatter(params) {
    if (params.value === undefined) return '$0.00';
    return '$' + params.value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function deleteIconCellRenderer() {
    return `<span class="delete-icon">🗑️</span>`;
}

function triggerAutoCalculationForAllRows() {
    const allNodes = [];
    window.grid.forEachNode((node) => allNodes.push(node));

    allNodes.forEach((node) => {
        const jobNumber = node.data.job_number;
        if (jobNumber) {
            const job = window.timesheet_data.jobs.find(j => j.job_number === jobNumber);
            if (job) {
                node.setDataValue('job_name', job.name);
                node.setDataValue('client', job.client_name);
                node.setDataValue('job_data', job);
            }
            calculateAmounts(node.data); // Reuse existing function
        }
    });

    // Refresh affected grid cells
    window.grid.refreshCells({
        rowNodes: allNodes,
        columns: ['job_name', 'client', 'wage_amount', 'bill_amount']
    });
}


function createNewRow() {
    return {
        id: null, // New rows start without an ID
        job_number: null, // Placeholder for job number
        timesheet_date: window.timesheet_data.timesheet_date, // Ensure timesheet_date is included
        staff_id: window.timesheet_data.staff.id, // Ensure staff_id is included
        is_billable: true, // Default value
        rate_type: 'Ord', // Default rate type
        hours: 0, // Default hours
        description: '', // Default description
    };
}

function calculateAmounts(data) {
    console.log('Calculating amounts for data:', data); // Log the data being processed
    const hours = data.hours || 0;
    const minutes = hours * 60;

    const rateMultiplier = {
        'Unpaid': 0.0,
        'Ord': 1.0,
        '1.5': 1.5,
        '2.0': 2.0
    }[data.rate_type] || 1.0;

    // Use staff wage rate from timesheet_data
    const wageRate = window.timesheet_data.staff.wage_rate;
    data.wage_amount = hours * wageRate * rateMultiplier;
    console.log('Calculated wage_amount:', data.wage_amount, 'with hours:', hours, 'wage_rate:', window.timesheet_data.staff.wage_rate, 'rateMultiplier:', rateMultiplier); // Log calculation details

    // Use job_data from the row to calculate bill amount
    const jobData = data.job_data;
    if (jobData) {
        data.bill_amount = hours * jobData.charge_out_rate;
    } else {
        data.bill_amount = 0; // Default to 0 if no matching job found
    }

    data.items = 1;
    data.mins_per_item = minutes;
}

const gridOptions = {
    columnDefs: [
        {
            field: 'id',
            hide: true, // Hidden column for the database ID
            editable: false,
        },
        {
            field: 'job_number',
            headerName: 'Job #',
            flex: 1,
            minWidth: 100,
            editable: true,
            cellEditor: ActiveJobCellEditor,
            cellEditorParams: {
                values: window.timesheet_data.jobs.map(job => job.job_display_name)
            }
        },
        {
            field: 'description',
            headerName: 'Description',
            flex: 2,
            minWidth: 150,
            editable: true
        },
        {
            field: 'hours',
            headerName: 'Hours',
            flex: 1,
            minWidth: 80,
            editable: true,
            type: 'numericColumn',
            valueParser: params => Number(params.newValue),
            valueFormatter: params => params.value?.toFixed(2)
        },
        {
            field: 'is_billable',
            headerName: 'Billable',
            width: 60,
            editable: true,
            cellRenderer: 'agCheckboxCellRenderer'
        },
        {
            field: 'notes',
            headerName: 'Notes',
            flex: 2,
            minWidth: 150,
            editable: true
        },
        {
            field: 'rate_type',
            headerName: 'Rate',
            width: 70,  // Set a specific width to make it smaller
            maxWidth: 70,  // REALLY TRY AND MAKE IT SMALLER
            editable: true,
            cellEditor: 'agSelectCellEditor',
            cellEditorParams: {
                values: ['Ord', '1.5', '2.0', 'Unpaid']
            }
        },
        {
            field: 'job_name',
            headerName: 'Job Name',
            width: 100,
            editable: false
        },
        {
            field: 'client', headerName: 'Client',
            width: 100,
            editable: false
        },
        {
            field: 'wage_amount',
            headerName: 'Wage $',
            width: 70,
            valueFormatter: currencyFormatter,
            editable: false
        },
        {
            field: 'bill_amount',
            headerName: 'Bill $',
            width: 70,
            valueFormatter: currencyFormatter,
            editable: false
        },
        {
            field: 'job_data',
            headerName: 'Job Data',
            width: 0,
            hide: true, // Invisible column to make processing easier
            editable: false
        },
        {
            field: 'staff_id',
            hide: true,  // Invisible column
            editable: false
        },
        {
            field: 'timesheet_date',
            hide: true,  // Invisible column
            editable: false
        },
        {
            headerName: '',
            width: 50,
            cellRenderer: deleteIconCellRenderer,
            onCellClicked: (params) => {
                const rowCount = params.api.getDisplayedRowCount();
                if (rowCount > 1) {  // Only allow delete if we have more than one row
                    params.api.applyTransaction({ remove: [params.node.data] });
                }
            }
        }
    ],
    defaultColDef: {
        flex: 1,
        minWidth: 100,
        sortable: false,
        filter: false
    },
    onCellValueChanged: (params) => {
        console.log('onCellValueChanged triggered:', params);
        // If job number changes, update job name, client, and job_data
        if (params.column?.colId === 'job_number') {
            console.log('Job number changed:', params.newValue);
            const job = window.timesheet_data.jobs.find(j => j.job_number === params.newValue);
            if (job) {
                params.node.setDataValue('job_name', job.name);
                params.node.setDataValue('client', job.client_name);
                params.node.setDataValue('job_data', job); // Store the whole job object as job_data

                calculateAmounts(params.node.data);
                console.log('Refreshing cells for job_name, client, wage_amount, bill_amount');
                params.api.refreshCells({
                    rowNodes: [params.node],
                    columns: ['job_name', 'client', 'wage_amount', 'bill_amount']
                });
            }
        }

        // Recalculate amounts if rate type or hours changes
        if (['rate_type', 'hours'].includes(params.column?.colId)) {
            console.log('Rate type or hours changed:', params.column.colId, params.newValue);
            calculateAmounts(params.node.data);
            console.log('Refreshing cells for wage_amount, bill_amount');
            params.api.refreshCells({
                rowNodes: [params.node],
                columns: ['wage_amount', 'bill_amount']
            });
        }
        console.log('Triggering autosave after cell value change.');
        debouncedAutosave();
    },
    // Add new row when Enter is pressed on last row
    onCellKeyDown: (params) => {
        if (params.event.key === 'Enter') {
            const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
            if (isLastRow) {
                params.api.applyTransaction({ add: [createNewRow()] }); // Use centralized function
                // Focus the first editable cell of the newly added row
                const newRowIndex = params.api.getDisplayedRowCount() - 1;
                params.api.setFocusedCell(newRowIndex, 'job_number');
            }
        }
    }
};

window.gridOptions = gridOptions;

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken')

document.addEventListener('DOMContentLoaded', function () {
    // Initialize the grid
    const gridDiv = document.querySelector('#timesheet-grid');
    window.grid = agGrid.createGrid(gridDiv, gridOptions);
    console.log('Grid object:', window.grid);

    // Load existing entries if any, otherwise add an empty row
    if (window.timesheet_data.time_entries?.length > 0) {
        window.grid.applyTransaction({ add: window.timesheet_data.time_entries });
        triggerAutoCalculationForAllRows();
    } else {
        window.grid.applyTransaction({
            add: [createNewRow()] // Use centralized function
        });
    }

    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

    const modal = $('#timesheetModal');

    // Handler for opening the modal
    $('#new-timesheet-btn').on('click', function (e) {
        e.preventDefault();

        console.log('Sending AJAX request...'); // Debug log

        $.ajax({
            url: window.location.pathname,
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: {
                action: 'load_form'
            }, // Remove csrfmiddlewaretoken from here since it's handled by ajaxSetup
            success: function (response) {
                console.log('Success:', response); // Debug log
                modal.find('.modal-body').html(response.form_html);
                modal.modal('show');
            },
            error: function (xhr, status, error) {
                console.error('Error:', {
                    status: status,
                    error: error,
                    response: xhr.responseText
                });
                alert('Error loading form. Please check console for details.');
            }
        });
    });

    // Handler for form submission
    modal.on('submit', '#timesheet-form', function (e) {
        e.preventDefault();
        const form = $(this);

        $.ajax({
            url: window.location.pathname,
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            data: form.serialize(), // form.serialize() will include the CSRF token automatically
            success: function (response) {
                if (response.success) {
                    window.grid.applyTransaction({ add: [response.entry] });
                    modal.modal('hide');
                }
            },
            error: function (xhr, status, error) {
                console.error('Error:', {
                    status: status,
                    error: error,
                    response: xhr.responseText
                });
                // Handle form errors here
            }
        });
    });
});