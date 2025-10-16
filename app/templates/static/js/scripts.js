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
            const currentUrl = window.location.href;
            
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

    // Initialize visibility on load
    const evidenceForm = document.querySelector('form#evidence-form');
    if (evidenceForm) {
        evidenceForm.addEventListener('change', updateEvidenceAutomatedCollection);
    }
    // Also listen for job template changes to autofill title/description
    const jobTemplateSelect = document.querySelector('[name="job_template_id"]');
    if (jobTemplateSelect) {
        jobTemplateSelect.addEventListener('change', updateEvidenceWithJobTemplate);
    }

    // Initialize components
    initComplianceChart();
});

/**
 * Toggle visibility of the automated collection fields inside the
 * evidence form based on the selected evidence type.
 *
 * This looks for a form with id `evidence-form` and a select named
 * `evidence_type`. When `evidence_type` equals `'automated_collection'`
 * the container with id `automated-collection-fields` is shown.
 *
 * @returns {void}
 */
function updateEvidenceAutomatedCollection() {
    const form = document.querySelector('form#evidence-form');
    if (!form) return;

    const evidenceTypeSelect = form.querySelector('[name="evidence_type"]');
    const automatedCollectionFields = form.querySelector('#automated-collection-fields');

    const value = evidenceTypeSelect ? evidenceTypeSelect.value : null;
    const isAuto = value === 'automated_collection';

    automatedCollectionFields.className = isAuto ? 'd-block' : 'd-none';
}

/**
 * Auto-fill the evidence title and description when a job template is selected.
 *
 * The function finds a hidden element with a matching `data-id` attribute
 * and reads its `[data-name]` and `[data-description]` child attributes.
 * These values are copied into the form fields named `title` and
 * `description` respectively.
 *
 * @param {Event} event - The change event from the job template select.
 * @returns {void}
 */
function updateEvidenceWithJobTemplate(event) {
    // `this` may be the select element if called with .call
    const select = event && event.target ? event.target : this;
    if (!select) return;

    const selectedValue = select.value;
    if (!selectedValue) return;

    // Find the hidden container with matching data-id
    const templateDiv = document.querySelector('#automated-collection-fields')
        ? document.querySelector('#automated-collection-fields').querySelector('[data-id="' + selectedValue + '"]')
        : document.querySelector('[data-id="' + selectedValue + '"]');

    if (!templateDiv) return;

    const name = templateDiv.querySelector('[data-name]');
    const desc = templateDiv.querySelector('[data-description]');

    const titleInput = document.querySelector('[name="title"]');
    const descriptionTextarea = document.querySelector('[name="description"]');

    if (name && desc) {
        titleInput.value = name.getAttribute('data-name');
        descriptionTextarea.value = desc.getAttribute('data-description');
    }
}

/*
 * Initialize the compliance chart
 */
function initComplianceChart() {
    const canvas = document.getElementById('compliance-chart');
    if (!canvas || typeof Chart === 'undefined') return;
    const data = {};

    Array.from(canvas.attributes).forEach((attr) => {
        if (!attr.name.startsWith('data-')) return;
        const label = attr.name.slice(5); // remove 'data-'
        const numericVal = parseInt(attr.value, 10);
        if (Number.isNaN(numericVal) || numericVal < 0) return;
        data[label] = numericVal;
    });
    // Map compliance labels to colors so the chart reflects semantic categories.
    const labelColorMap = {
        'compliant': '#2e8540',
        'non_compliant': '#f9c700ff',
        'error': '#cb0f0fff',
        'insufficient_data': '#1f58f6ff',
        'not_applicable': '#898989ff'
    };

    // Primary order defined by labelColorMap, then any extra labels encountered.
    const orderedPrimary = Object.keys(labelColorMap).filter((key) => Object.prototype.hasOwnProperty.call(data, key));
    const extra = Object.keys(data).filter((l) => !orderedPrimary.includes(l));
    const sortedLabels = [...orderedPrimary, ...extra];
    const sortedValues = sortedLabels.map((l) => data[l]);
    const backgroundColor = sortedLabels.map((l) => labelColorMap[l] || '#eee');

    new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: sortedLabels,
            datasets: [{
                data: sortedValues,
                backgroundColor,
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            cutout: '60%',
            plugins: {
                legend: {
                    position: 'bottom', 
                    labels: {
                        filter: (legendItem, data) => data.datasets[0].data[legendItem.index] != 0
                    }
                }
            }
        }
    });
}

/**
 * Reload the current page content and inject it into the #main-content element.
 * Also updates CSRF tokens across the entire page if present.
 *
 * @returns {Promise<void>}
 */
async function reloadPageContent() {
    try {
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
            }
        }
    } catch (error) {
        console.error('Failed to reload page content:', error);
    }
}


