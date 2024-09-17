function filterClients() {
    const searchTerm = document.getElementById('search').value.toLowerCase();
    document.querySelectorAll('.client-row').forEach(row => {
        const name = row.dataset.name || '';
        const email = row.dataset.email || '';
        const phone = row.dataset.phone || '';
        const address = row.dataset.address || '';
        const accountCustomer = row.dataset.accountCustomer || '';

        const combinedText = [name, email, phone, address, accountCustomer].join(' ').toLowerCase();

        if (combinedText.includes(searchTerm)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', filterClients);
    }
});