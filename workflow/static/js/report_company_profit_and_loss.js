document.addEventListener("DOMContentLoaded", function () {
  const dateRanges = {
    "This month": {
      dates: [moment().startOf("month"), moment().endOf("month")],
      periodType: "month",
    },
    "Last month": {
      dates: [
        moment().subtract(1, "month").startOf("month"),
        moment().subtract(1, "month").endOf("month"),
      ],
      periodType: "month",
    },
    "This quarter": {
      dates: [moment().startOf("quarter"), moment().endOf("quarter")],
      periodType: "quarter",
    },
    "Last quarter": {
      dates: [
        moment().subtract(1, "quarter").startOf("quarter"),
        moment().subtract(1, "quarter").endOf("quarter"),
      ],
      periodType: "quarter",
    },
    "This financial year": {
      dates: [
        moment().month(3).startOf("month"),
        moment().add(1, "year").month(2).endOf("month"),
      ],
      periodType: "year",
    },
    "Last financial year": {
      dates: [
        moment().subtract(1, "year").month(3).startOf("month"),
        moment().month(2).endOf("month"),
      ],
      periodType: "year",
    },
    "Custom date range": {
      dates: [null, null],
      periodType: null,
    },
  };

  const datePicker = document.getElementById("date-range-picker");
  const fromDateField = document.getElementById("date-from");
  const toDateField = document.getElementById("date-to");
  const compareField = document.getElementById("compare-periods");
  const periodTypeField = document.getElementById("period-type");

  // Initialize the grid with default columns
  const gridDiv = document.getElementById("pnl-grid");
  const gridOptions = {
    columnDefs: [
      { field: "category", headerName: "Category", pinned: "left", flex: 1 },
      {
        field: "subCategory",
        headerName: "Subcategory",
        pinned: "left",
        flex: 1,
      },
    ],
    defaultColDef: {
      flex: 1,
      sortable: true,
      filter: true,
    },
  };

  const api = agGrid.createGrid(gridDiv, gridOptions);

  // Populate dropdown with options
  Object.keys(dateRanges).forEach((rangeName) => {
    const option = document.createElement("option");
    option.value = rangeName;
    option.textContent = rangeName;
    datePicker.appendChild(option);
  });

  function updateDateFields(rangeName) {
    const selectedRange = dateRanges[rangeName];
    if (selectedRange) {
      const [start, end] = selectedRange.dates;

      if (start && end) {
        fromDateField.value = start.format("YYYY-MM-DD");
        toDateField.value = end.format("YYYY-MM-DD");
        periodTypeField.value = selectedRange.periodType;
        compareField.value = "0";
      } else {
        fromDateField.value = "";
        toDateField.value = "";
        periodTypeField.value = "month";
      }
    }
  }

  datePicker.addEventListener("change", function () {
    updateDateFields(this.value);
    triggerUpdateReport();
  });

  fromDateField.addEventListener("change", () => {
    datePicker.value = "Custom date range";
    triggerUpdateReport();
  });
  toDateField.addEventListener("change", () => {
    datePicker.value = "Custom date range";
    triggerUpdateReport();
  });

  function triggerUpdateReport() {
    const startDate = fromDateField.value;
    const endDate = toDateField.value;
    const comparePeriods = compareField.value;
    const periodType = periodTypeField.value;

    if (!startDate || !endDate || !comparePeriods) {
      alert("Please ensure all fields are filled in.");
      return;
    }

    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
      compare: comparePeriods,
      period_type: periodType,
    });

    fetch(`/api/reports/company-profit-loss/?${params}`)
      .then((response) => response.json())
      .then((data) => {
        const rowData = [];
        const categories = [
          "Trading Income",
          "Cost of Sales",
          "Operating Expenses",
          "Equity Movements",
          "Other Items",
        ];

        categories.forEach((category) => {
          Object.entries(data[category] || {}).forEach(
            ([accountName, values]) => {
              rowData.push({
                category: category,
                subCategory: accountName,
                expanded: true,
                ...values.reduce((acc, value, idx) => {
                  acc[`period${idx + 1}`] = parseFloat(value);
                  return acc;
                }, {}),
              });
            },
          );
        });

        Object.entries(data.totals).forEach(([key, values]) => {
          rowData.push({
            category: "TOTAL",
            subCategory: key.replace(/_/g, " ").toUpperCase(),
            ...values.reduce((acc, value, idx) => {
              acc[`period${idx + 1}`] = parseFloat(value);
              return acc;
            }, {}),
          });
        });

        const numPeriods = Math.max(
          ...rowData.map(
            (row) =>
              Object.keys(row).filter((key) => key.startsWith("period")).length,
          ),
        );

        const periodColumns = Array.from({ length: numPeriods }, (_, i) => ({
          field: `period${i + 1}`,
          headerName: `Period ${i + 1}`,
          valueFormatter: (params) => {
            if (params.value === undefined) return "";
            const formatted = Math.round(params.value).toString();
            return params.value < 0
              ? formatted.replace("-", "-$")
              : "$" + formatted;
          },
          cellStyle: (params) => ({
            color: params.value < 0 ? "red" : "black",
            textAlign: "right",
          }),
        }));

        // Update grid columns
        const newColumnDefs = [
          {
            field: "description",
            headerName: " ",
            pinned: "left",
            flex: 1,
            valueGetter: (params) => {
              if (params.data.category === "TOTAL") {
                return params.data.subCategory;
              }
              return params.data.category === params.data.subCategory
                ? params.data.category
                : `    ${params.data.subCategory}`;
            },
          },
          ...periodColumns,
        ];
        api.setGridOption("columnDefs", newColumnDefs);
        api.setGridOption("rowData", rowData);
      })
      .catch((error) => {
        console.error("Error fetching P&L data:", error);
        alert("Failed to load report data. Please try again.");
      });
  }

  // Initial load
  updateDateFields("Last month");
  triggerUpdateReport();
});
