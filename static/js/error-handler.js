/**
 * Error/Validation Handler Utility
 * Displays validation and error messages via the global Femtrack toast stack.
 */

function _showToastErrors(errors) {
    if (typeof window.showFemtrackErrors === 'function') {
        window.showFemtrackErrors(errors);
        return;
    }
    const list = Array.isArray(errors) ? errors : [errors];
    list.filter(Boolean).forEach(error => {
        if (typeof window.showFemtrackToast === 'function') {
            window.showFemtrackToast(error, 'danger');
        } else {
            console.error(error);
        }
    });
}

/**
 * Create a toast-backed error helper for a form container.
 * @param {string} containerId - ID of the container (kept for API compatibility)
 * @param {string} errorBoxId - Unused; kept for API compatibility
 * @returns {object|null} Object with methods: show(), hide(), add(), clear()
 */
function createErrorBox(containerId, errorBoxId = 'errorBox') {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Container with ID "${containerId}" not found`);
        return null;
    }

    let pendingErrors = [];

    return {
        show: function(errors) {
            this.clear();
            this.add(errors);
            _showToastErrors(pendingErrors);
        },
        hide: function() {
            pendingErrors = [];
        },
        add: function(errors) {
            if (!Array.isArray(errors)) {
                errors = [errors];
            }
            pendingErrors.push(...errors.filter(Boolean));
        },
        clear: function() {
            pendingErrors = [];
        },
        isVisible: function() {
            return pendingErrors.length > 0;
        },
        autoHideOnInput: function(formSelector = 'input, textarea, select') {
            const inputs = container.querySelectorAll(formSelector);
            inputs.forEach(input => {
                input.addEventListener('change', () => this.hide());
                input.addEventListener('input', () => this.hide());
            });
        }
    };
}

function showValidationErrors(boxId, errors) {
    _showToastErrors(errors);
}

function hideValidationErrors() {
    /* Toasts auto-dismiss; nothing to hide. */
}

function clearValidationErrors() {
    /* Toasts auto-dismiss; nothing to clear. */
}
