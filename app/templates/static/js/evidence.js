document.addEventListener('DOMContentLoaded', () => {
    new ImageOverlay();

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