document.addEventListener('DOMContentLoaded', function() {
    console.log("DOMContentLoaded event fired - attempting to convert UTC to NZT");
    var timeElements = document.querySelectorAll('.utc-time');

    timeElements.forEach(function(el) {
        var utcTimeStr = el.getAttribute('data-utc');
        console.log("Original UTC time (before conversion):", utcTimeStr);

        if (utcTimeStr) {
            // Create a Date object from the UTC string
            var utcTime = new Date(utcTimeStr);

            // Convert the Date object to the local time of the user's browser
            // Assuming user is in NZ, the browser will automatically convert to local time
            var nztTime = utcTime.toLocaleString('en-NZ', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
            }).replace(/\//g, '/').replace(',', ' at');

            // Log the converted NZ time
            console.log("Converted NZ time (after conversion):", nztTime);

            // Set the converted time to the element's value (since it's an input element)
            el.value = nztTime;
        } else {
            console.warn("No valid UTC time found for element:", el);
        }
    });

    console.log("Finished converting all time elements.");
});
