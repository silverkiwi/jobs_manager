document.addEventListener('DOMContentLoaded', function() {
    var timeElements = document.querySelectorAll('.utc-time');
    timeElements.forEach(function(el) {
        var utcTime = new Date(el.getAttribute('data-utc'));
        el.textContent = utcTime.toLocaleString('en-NZ', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        }).replace(/\//g, '/').replace(',', ' at');
    });
});