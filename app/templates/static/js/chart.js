/**
 * Initialize a compliance pie chart from a canvas element.
 * The canvas must have data attributes matching compliance status keys,
 * e.g., data-compliant, data-non_compliant, etc.
 *
 * @param {string|HTMLCanvasElement} canvasIdOrElement - The canvas ID or element to render the chart on.
 * @returns {Chart|null} The Chart.js instance, or null if canvas or Chart library not found.
 */
function initComplianceChart(canvas) {

    if (!canvas || typeof Chart === 'undefined') return null;

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
        'not_applicable': '#898989ff',
        'partially_compliant': '#f9c700ff',
        'pending': '#898989ff',
        'unknown': '#898989ff',
    };

    // Primary order defined by labelColorMap, then any extra labels encountered.
    const orderedPrimary = Object.keys(labelColorMap).filter((key) => Object.prototype.hasOwnProperty.call(data, key));
    const extra = Object.keys(data).filter((l) => !orderedPrimary.includes(l));
    const sortedLabels = [...orderedPrimary, ...extra];
    const sortedValues = sortedLabels.map((l) => data[l]);
    const backgroundColor = sortedLabels.map((l) => labelColorMap[l] || '#eee');

    return new Chart(canvas, {
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
 * Initialize all compliance charts on the page.
 * Looks for canvas elements with the class 'compliance-chart'.
 *
 * @returns {void}
 */
function initAllComplianceCharts() {
    const charts = document.querySelectorAll('canvas.compliance-chart');
    charts.forEach((canvas) => {
        initComplianceChart(canvas);
    });
}

// Auto-initialize charts on DOMContentLoaded
document.addEventListener('DOMContentLoaded', initAllComplianceCharts);
