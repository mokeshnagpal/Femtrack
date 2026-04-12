/**
 * Error/Validation Handler Utility
 * Provides reusable functions for displaying and managing error/validation messages
 * across the entire application
 */

/**
 * Create and display an error/validation message box
 * @param {string} containerId - ID of the container where error box should be inserted
 * @param {string} errorBoxId - ID for the error box (default: 'errorBox')
 * @returns {object} Object with methods: show(), hide(), add(), clear()
 */
function createErrorBox(containerId, errorBoxId = 'errorBox') {
    const container = document.getElementById(containerId);
    
    if (!container) {
        console.error(`Container with ID "${containerId}" not found`);
        return null;
    }

    // Create error box HTML
    const errorBox = document.createElement('div');
    errorBox.id = errorBoxId;
    errorBox.className = 'alert alert-danger alert-dismissible fade show d-none mb-4';
    errorBox.setAttribute('role', 'alert');
    
    errorBox.innerHTML = `
        <div class="d-flex align-items-start">
            <div style="flex: 1;">
                <h5 class="alert-heading mb-3">
                    <i class="fas fa-exclamation-triangle"></i> Validation Errors
                </h5>
                <ul id="${errorBoxId}-list" class="mb-0 ps-0 list-unstyled">
                </ul>
            </div>
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    // Insert at the beginning of the container
    container.insertBefore(errorBox, container.firstChild);

    // Return API object
    return {
        element: errorBox,
        listElement: document.getElementById(`${errorBoxId}-list`),
        
        /**
         * Show error box with errors
         * @param {array} errors - Array of error messages
         */
        show: function(errors) {
            this.clear();
            this.add(errors);
            this.element.classList.remove('d-none');
            this.element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        },
        
        /**
         * Hide error box
         */
        hide: function() {
            this.element.classList.add('d-none');
        },
        
        /**
         * Add error messages
         * @param {array} errors - Array of error messages to add
         */
        add: function(errors) {
            if (!Array.isArray(errors)) {
                errors = [errors];
            }
            
            errors.forEach(error => {
                const li = document.createElement('li');
                li.className = 'mb-2';
                li.innerHTML = '<i class="fas fa-exclamation-circle"></i> ' + error;
                this.listElement.appendChild(li);
            });
        },
        
        /**
         * Clear all errors
         */
        clear: function() {
            this.listElement.innerHTML = '';
        },
        
        /**
         * Check if error box is visible
         */
        isVisible: function() {
            return !this.element.classList.contains('d-none');
        },
        
        /**
         * Add click listener to form inputs to auto-hide errors
         * @param {string} formSelector - CSS selector for form inputs
         */
        autoHideOnInput: function(formSelector = 'input, textarea, select') {
            const inputs = this.element.parentElement.querySelectorAll(formSelector);
            inputs.forEach(input => {
                input.addEventListener('change', () => this.hide());
                input.addEventListener('input', () => this.hide());
            });
        }
    };
}

/**
 * Quick helper: Display validation errors inline
 * @param {string} boxId - ID of the error box
 * @param {array} errors - Array of error messages
 */
function showValidationErrors(boxId, errors) {
    const box = document.getElementById(boxId);
    if (!box) {
        console.error(`Error box with ID "${boxId}" not found`);
        return;
    }
    
    const errorList = box.querySelector('ul');
    if (!errorList) {
        console.error(`Error list not found in box "${boxId}"`);
        return;
    }
    
    errorList.innerHTML = '';
    
    if (!Array.isArray(errors)) {
        errors = [errors];
    }
    
    errors.forEach(error => {
        const li = document.createElement('li');
        li.className = 'mb-2';
        li.innerHTML = '<i class="fas fa-exclamation-circle"></i> ' + error;
        errorList.appendChild(li);
    });
    
    box.classList.remove('d-none');
    box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Quick helper: Hide validation errors by box ID
 * @param {string} boxId - ID of the error box
 */
function hideValidationErrors(boxId) {
    const box = document.getElementById(boxId);
    if (box) {
        box.classList.add('d-none');
    }
}

/**
 * Quick helper: Clear validation errors by box ID
 * @param {string} boxId - ID of the error box
 */
function clearValidationErrors(boxId) {
    const box = document.getElementById(boxId);
    if (box) {
        const errorList = box.querySelector('ul');
        if (errorList) {
            errorList.innerHTML = '';
        }
    }
}
