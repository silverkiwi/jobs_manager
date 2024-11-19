document.addEventListener('DOMContentLoaded', function() {
   function currencyFormatter(params) {
       if (params.value === undefined) return '$0.00';
       return '$' + params.value.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
   }

   function deleteIconCellRenderer() {
       return `<span class="delete-icon">🗑️</span>`;
   }

function calculateAmounts(data) {
    const hours = data.hours || 0;
    const minutes = hours * 60;

    const rateMultiplier = {
        'Ord': 1.0,
        '1.5': 1.5,
        '2.0': 2.0
    }[data.rate_type] || 1.0;

    // Use staff wage rate from timesheet_data
    data.wage_amount = hours * window.timesheet_data.wage_rate * rateMultiplier;
    // Use job's charge out rate
    data.bill_amount = hours * data.charge_out_rate;

    data.items = 1;
    data.mins_per_item = minutes;
}

   const gridOptions = {
       columnDefs: [
           {
               field: 'job_number',
               headerName: 'Job #',
               width: 80,
               editable: true,
               cellEditor: 'agRichSelectCellEditor',
               cellEditorParams: {
                   values: window.timesheet_data.jobs.map(job => ({
                       value: job.job_number,
                       label: `${job.job_number} - ${job.name}`
                   }))
               }
           },
           {
               field: 'job_name',
               headerName: 'Job Name',
               width: 150,
               editable: false
           },
           {
               field: 'customer',
               headerName: 'Customer',
               width: 150,
               editable: false
           },
           {
               field: 'description',
               headerName: 'Description',
               flex: 2,
               minWidth: 200,
               editable: true
           },
           {
               field: 'rate_type',
               headerName: 'Rate',
               width: 80,
               editable: true,
               cellEditor: 'agSelectCellEditor',
               cellEditorParams: {
                   values: ['Ord', '1.5', '2.0']
               },
               defaultValue: 'Ord'
           },
           {
               field: 'hours',
               headerName: 'Hours',
               width: 80,
               editable: true,
               type: 'numericColumn',
               valueParser: params => Number(params.newValue),
               valueFormatter: params => params.value?.toFixed(2)
           },
           {
               field: 'wage_amount',
               headerName: 'Wage $',
               width: 100,
               valueFormatter: currencyFormatter,
               editable: false
           },
           {
               field: 'bill_amount',
               headerName: 'Bill $',
               width: 100,
               valueFormatter: currencyFormatter,
               editable: false
           },
           {
               field: 'is_billable',
               headerName: 'Billable',
               width: 80,
               editable: true,
               cellRenderer: 'agCheckboxCellRenderer',
               defaultValue: true
           },
           {
               field: 'notes',
               headerName: 'Notes',
               flex: 1,
               minWidth: 200,
               editable: true
           },
           {
               headerName: '',
               width: 50,
               cellRenderer: deleteIconCellRenderer,
               onCellClicked: (params) => {
                   params.api.applyTransaction({remove: [params.node.data]});
               }
           }
       ],
       defaultColDef: {
           sortable: true,
           filter: true
       },
       onCellValueChanged: (params) => {
           // If job number changes, update job name and customer
if (params.column.colId === 'job_number') {
            const job = window.timesheet_data.jobs.find(j => j.job_number === params.newValue);
            if (job) {
                params.node.setDataValue('job_name', job.name);
                params.node.setDataValue('customer', job.client_name);
                // Don't set wage_rate as it comes from staff
                params.node.setDataValue('charge_out_rate', job.charge_out_rate);
                calculateAmounts(params.node.data);
                params.api.refreshCells({
                    rowNodes: [params.node],
                    columns: ['job_name', 'customer', 'wage_amount', 'bill_amount']
                });
            }
        }

           // Recalculate amounts if rate type or hours changes
           if (['rate_type', 'hours'].includes(params.column.colId)) {
               calculateAmounts(params.node.data);
               params.api.refreshCells({
                   rowNodes: [params.node],
                   columns: ['wage_amount', 'bill_amount']
               });
           }
       },
       // Add new row when Enter is pressed on last row
       onCellKeyDown: (params) => {
           if (params.event.key === 'Enter') {
               const isLastRow = params.api.getDisplayedRowCount() - 1 === params.rowIndex;
               if (isLastRow) {
                   const newRow = {
                       is_billable: true,
                       rate_type: 'Ord'
                   };
                   params.api.applyTransaction({add: [newRow]});
               }
           }
       }
   };

   // Initialize the grid
   const gridDiv = document.querySelector('#timesheet-grid');
   new agGrid.Grid(gridDiv, gridOptions);

   // Load existing entries if any, otherwise add an empty row
   if (window.timesheet_data.time_entries?.length > 0) {
       gridOptions.api.applyTransaction({ add: window.timesheet_data.time_entries });
   } else {
       gridOptions.api.applyTransaction({
           add: [{
               is_billable: true,
               rate_type: 'Ord'
           }]
       });
   }
});