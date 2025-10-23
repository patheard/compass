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

document.addEventListener('DOMContentLoaded', () => {
    new ImageOverlay();

    const evidenceForm = document.querySelector('form#evidence-form');
    if (evidenceForm) {
        evidenceForm.addEventListener('change', updateEvidenceAutomatedCollection);
    }
    const jobTemplateSelect = document.querySelector('[name="job_template_id"]');
    if (jobTemplateSelect) {
        jobTemplateSelect.addEventListener('change', updateEvidenceWithJobTemplate);
    }

    const uploadContainer = document.getElementById('fileUploadContainer');
    if (uploadContainer) {
        const isEditMode = uploadContainer.dataset.editMode === 'true';
        const assessmentId = uploadContainer.dataset.assessmentId || '';
        const controlId = uploadContainer.dataset.controlId || '';
        const evidenceId = uploadContainer.dataset.evidenceId || '';
        const csrfToken = uploadContainer.dataset.csrfToken || '';

        new FileUploadWidget(uploadContainer, {
            isEditMode,
            assessmentId,
            controlId,
            evidenceId,
            csrfToken
        });
    }
});