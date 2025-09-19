/**
 * Main JavaScript functionality for the Compass application
 */

/**
 * Delete an item by sending a POST request to the delete endpoint
 * @param {string} deleteUrl - The URL of the delete endpoint
 * @param {string} csrfToken - The CSRF token for the request
 */
async function deleteItem(deleteUrl, csrfToken) {
    try {
        const response = await fetch(deleteUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'csrf_token': csrfToken
            })
        });

        // Handle both successful deletion (200) and redirect (3xx)
        if (response.ok || response.redirected) {
            window.location.href = response.url || '/';
        } else {
            console.error('Failed to delete item:', response.status);
        }
    } catch (error) {
        console.error('Error deleting item:', error);
    }
}

/**
 * Initialize event handlers when the DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    // Bind all delete buttons (assessments, controls, evidence)
    const deleteButtons = document.querySelectorAll('gcds-button.delete-item');
    deleteButtons.forEach(function(deleteBtn) {
        deleteBtn.addEventListener('click', function(event) {
            event.preventDefault(); // Prevent default link behavior
            const deleteUrl = this.getAttribute('href');
            const csrfToken = this.getAttribute('data-csrf-token');
            deleteItem(deleteUrl, csrfToken);
        });
    });
});