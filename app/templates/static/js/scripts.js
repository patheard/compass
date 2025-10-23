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

        if (response.ok || response.redirected) {
            const redirectUrl = response.url;
            const currentUrl = window.location.origin + window.location.pathname + window.location.search;

            if (redirectUrl === currentUrl) {
                await reloadPageContent();
            } else {
                window.location.href = redirectUrl;
            }
        } else {
            console.error('Failed to delete item:', response.status);
        }
    } catch (error) {
        console.error('Error deleting item:', error);
    }
}

/**
 * Show a generic confirmation modal and wire up its controls.
 * The modal is assumed to exist in the DOM with IDs `confirmModal`,
 * `modalConfirm`, and `modalCancel`. When the confirm button is clicked
 * the provided callback is executed after the modal is hidden.
 *
 * @param {Function} onConfirm - Callback executed when the user confirms.
 * @returns {void}
 */
function showConfirmModal(onConfirm) {
    const modal = document.getElementById('confirmModal');
    const confirmBtn = document.getElementById('modalConfirm');
    const cancelBtn = document.getElementById('modalCancel');

    // Show modal
    modal.classList.add('show');
    
    // Handle confirm
    confirmBtn.onclick = function() {
        hideConfirmModal();
        onConfirm();
    };
    
    // Handle cancel
    cancelBtn.onclick = hideConfirmModal;
    
    // Handle clicking outside modal
    modal.onclick = function(event) {
        if (event.target === modal) {
            hideConfirmModal();
        }
    };
}

/**
 * Hide the confirmation modal and clear any attached event handlers.
 * This prevents leaked references to callbacks and ensures that the
 * modal can be reused safely.
 *
 * @returns {void}
 */
function hideConfirmModal() {
    const modal = document.getElementById('confirmModal');
    modal.classList.remove('show');
    
    // Clear event handlers;
    document.getElementById('modalConfirm').onclick = null;
    document.getElementById('modalCancel').onclick = null;
    modal.onclick = null;
}

/**
 * Initialize event handlers and UI components after DOMContentLoaded.
 * Binds delete buttons to the confirmation flow, wires form change
 * events for evidence automation, initializes the compliance chart
 * and sliding panel components.
 *
 * @returns {void}
 */
document.addEventListener('DOMContentLoaded', function() {
    document.querySelector('#main-content').addEventListener('click', function(event) {
        const deleteBtn = event.target.closest && event.target.closest('.delete-item');
        if (deleteBtn) {
            event.preventDefault();
            const deleteUrl = deleteBtn.getAttribute('href');
            const csrfToken = deleteBtn.getAttribute('data-csrf-token');
            showConfirmModal(function() {
                deleteItem(deleteUrl, csrfToken);
            });
        }
    });
});

/**
 * Reload the current page content and inject it into the #main-content element.
 * Also updates CSRF tokens across the entire page if present.
 *
 * @returns {Promise<void>}
 */
async function reloadPageContent() {
    try {
        // Store current hash to restore tab selection
        const activeHash = window.location.hash;

        const pageResponse = await fetch(window.location.pathname);
        if (pageResponse.ok) {
            const html = await pageResponse.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newContent = doc.querySelector('#main-content');
            const currentContent = document.querySelector('#main-content');
            
            if (newContent && currentContent) {
                currentContent.innerHTML = newContent.innerHTML;

                // Check if there are any CSRF tokens to update
                const csrfElement = newContent.querySelector('[data-csrf-token]');
                if (csrfElement) {
                    const csrfToken = csrfElement.getAttribute('data-csrf-token');
                    document.querySelectorAll('[data-csrf-token]').forEach((element) => {
                        element.setAttribute('data-csrf-token', csrfToken);
                    });
                }

                // Restore tab selection via hash if present
                if (activeHash) {
                    const event = new HashChangeEvent('hashchange', {
                        newURL: window.location.href,
                        oldURL: window.location.href
                    });
                    window.dispatchEvent(event);
                }
            }
        }
    } catch (error) {
        console.error('Failed to reload page content:', error);
    }
}
