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
 * Show confirmation modal
 * @param {Function} onConfirm - Callback function when confirmed
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
 * Hide confirmation modal
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
 * Initialize event handlers when the DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    // Bind all delete buttons (assessments, controls, evidence)
    const deleteButtons = document.querySelectorAll('.delete-item');
    deleteButtons.forEach(function(deleteBtn) {
        deleteBtn.addEventListener('click', function(event) {
            event.preventDefault(); // Prevent default link behavior
            const deleteUrl = this.getAttribute('href');
            const csrfToken = this.getAttribute('data-csrf-token');
            
            showConfirmModal(function() {
                deleteItem(deleteUrl, csrfToken);
            });
        });
    });

    // Initialize visibility on load
    const evidenceForm = document.querySelector('form#evidence-form');
    if (evidenceForm) {
        evidenceForm.addEventListener('change', updateEvidenceAutomatedCollection);
    }

    // Initialize compliance chart if present
    initComplianceChart();
});

/**
 * Update visibility and required attributes for automated collection related fields.
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
 * Initialize the compliance donut chart if the canvas exists.
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