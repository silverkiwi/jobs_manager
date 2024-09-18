document.addEventListener('DOMContentLoaded', function() {
    // Fetch data from the API
    fetch('/api/company-profit-and-loss-report/')
      .then(response => response.json())
      .then(data => {
          const months = data.months;
          const categories = data.categories;

          // Build the table header
          let tableHtml = '<table class="table">';
          tableHtml += '<thead><tr><th>Category</th>';
          months.forEach(month => {
              tableHtml += `<th>${month}</th>`;
          });
          tableHtml += '</tr></thead><tbody>';

          // Iterate through each category (Income, Cost of Sales, etc.)
          for (const category in categories) {
              tableHtml += `<tr><th colspan="${months.length + 1}">${category}</th></tr>`;
              const subCategories = categories[category];

              // Iterate through each sub-category
              for (const subCategory in subCategories) {
                  const values = subCategories[subCategory];
                  tableHtml += `<tr><td>${subCategory}</td>`;
                  values.forEach(value => {
                      tableHtml += `<td>${value.toLocaleString()}</td>`;
                  });
                  tableHtml += '</tr>';
              }
          }

          tableHtml += '</tbody></table>';

          // Insert the table into the DOM
          document.getElementById('report-table').innerHTML = tableHtml;
      });
});
