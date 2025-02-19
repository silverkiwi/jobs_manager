function deleteIconCellRenderer(params) {
    const isLastRow = params.api.getDisplayedRowCount() === 1;
    const iconClass = isLastRow ? 'delete-icon disabled' : 'delete-icon';
    return `<span class='${iconClass}'>🗑️</span>`;
}

function onDeleteIconClicked(params) {
    if (params.api.getDisplayedRowCount() > 1) {
        params.api.applyTransaction({ remove: [params.node.data] });
        calculateTotalRevenue(); // Recalculate totals after row deletion
    }
}

export function createTrashCanColumn() {
    return {
        headerName: '',
        field: '',
        width: 40,
        cellRenderer: deleteIconCellRenderer,
        onCellClicked: onDeleteIconClicked,
        cellStyle: {
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            padding: 0
        }
    };
}