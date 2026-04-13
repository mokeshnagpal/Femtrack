// Femtrack - Global JavaScript initialization
console.log('Femtrack loaded successfully');

// Initialize tooltips and other Bootstrap components on page load
document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap tooltips initialization (if needed)
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
