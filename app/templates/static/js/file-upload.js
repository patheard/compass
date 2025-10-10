/**
 * Drag and drop file upload component for evidence forms
 */
class FileUploadWidget {
    constructor(uploadContainer, options = {}) {
        this.container = uploadContainer;
        if (!this.container) {
            console.error(`Container not found`);
            return;
        }

        this.maxFileSize = 5 * 1024 * 1024; // 5MB
        this.maxTotalSize = 5 * 1024 * 1024; // 5MB total
        this.allowedExtensions = ['.jpg', '.jpeg', '.png', '.webp', '.md', '.pdf'];
        this.files = new Map();
        this.existingFiles = new Map();
        this.filesToDelete = new Set();
        this.fileIdCounter = 0;

        this.isEditMode = options.isEditMode || false;
        this.assessmentId = options.assessmentId || '';
        this.controlId = options.controlId || '';
        this.evidenceId = options.evidenceId || '';
        this.csrfToken = options.csrfToken || '';

        if (!this.evidenceId || !this.assessmentId || !this.controlId || !this.csrfToken) {
            console.error('Missing required options for FileUploadWidget');
            return;
        }

        this.init();
    }

    async init() {       
        if (this.isEditMode && this.evidenceId) {
            await this.loadExistingFiles();
        }
        this.attachEventListeners();
        this.updateFileList();
    }

    async loadExistingFiles() {
        try {
            const response = await fetch(
                `/assessments/${this.assessmentId}/controls/${this.controlId}/evidence/${this.evidenceId}/files/metadata`
            );
            
            if (!response.ok) {
                throw new Error('Failed to load existing files');
            }

            const filesMetadata = await response.json();
            
            for (const metadata of filesMetadata) {
                this.existingFiles.set(metadata.key, metadata);
            }
        } catch (error) {
            console.error('Error loading existing files:', error);
        }
    }

    attachEventListeners() {
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const fileSelectButton = document.querySelector('.file-select-button');

        // Handle file select button click
        if (fileSelectButton) {
            fileSelectButton.addEventListener('click', (e) => {
                e.preventDefault();
                fileInput.click();
            });
        }

        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        // Highlight drop zone when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('drop-zone-active');
            });
        });
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('drop-zone-active');
            });
        });

        // Handle dropped files
        dropZone.addEventListener('drop', (e) => {
            const droppedFiles = Array.from(e.dataTransfer.files);
            this.handleFiles(droppedFiles);
        });

        // Handle file input change
        fileInput.addEventListener('change', (e) => {
            const selectedFiles = Array.from(e.target.files);
            this.handleFiles(selectedFiles);
        });

        // Handle form submission to include files
        const form = this.container.closest('form');
        if (form) {
            form.addEventListener('submit', (e) => {
                this.attachFilesToForm(form);
            });
        }
    }

    handleFiles(newFiles) {
        const errors = [];

        for (const file of newFiles) {
            // Validate file extension
            const ext = this.getFileExtension(file.name);
            if (!this.allowedExtensions.includes(ext)) {
                errors.push(`${file.name}: Invalid file type. Allowed types: ${this.allowedExtensions.join(', ')}`);
                continue;
            }

            // Validate individual file size
            if (file.size > this.maxFileSize) {
                errors.push(`${file.name}: File size (${this.formatFileSize(file.size)}) exceeds maximum of 5 MB`);
                continue;
            }

            // Check if file already exists (by name)
            let fileExists = false;
            for (const [id, existingFile] of this.files) {
                if (existingFile.name === file.name) {
                    fileExists = true;
                    break;
                }
            }

            if (fileExists) {
                errors.push(`${file.name}: File already added`);
                continue;
            }

            // Add file with unique ID
            const fileId = this.fileIdCounter++;
            this.files.set(fileId, file);
        }

        // Validate total size
        const totalSize = this.getTotalSize();
        if (totalSize > this.maxTotalSize) {
            // Remove files that were just added
            for (const file of newFiles) {
                for (const [id, f] of this.files) {
                    if (f.name === file.name) {
                        this.files.delete(id);
                        break;
                    }
                }
            }
            errors.push(`Total file size would exceed 5MB limit. Current total: ${this.formatFileSize(totalSize)}`);
        }

        if (errors.length > 0) {
            this.showErrors(errors);
        } else {
            this.hideErrors();
        }

        this.updateFileList();
    }

    removeFile(fileId) {
        this.files.delete(fileId);
        this.updateFileList();
        this.hideErrors();
    }

    removeExistingFile(fileKey) {
        // Mark file for deletion (don't delete immediately)
        if (this.filesToDelete.has(fileKey)) {
            // Unmark for deletion
            this.filesToDelete.delete(fileKey);
        } else {
            // Mark for deletion
            this.filesToDelete.add(fileKey);
        }
        this.updateFileList();
        this.hideErrors();
    }

    updateFileList() {
        const existingFileList = document.getElementById('existingFileList');
        const existingFileListItems = document.getElementById('existingFileListItems');
        const fileList = document.getElementById('fileList');
        const fileListItems = document.getElementById('fileListItems');
        const totalSizeElement = document.getElementById('totalSize');

        // Update existing files list
        if (this.existingFiles.size === 0) {
            existingFileList.classList.add('d-none');
        } else {
            existingFileList.classList.remove('d-none');
            existingFileListItems.innerHTML = '';

            for (const [fileKey, metadata] of this.existingFiles) {
                const isMarkedForDeletion = this.filesToDelete.has(fileKey);
                const tr = document.createElement('tr');
                tr.className = 'file-list-item' + (isMarkedForDeletion ? ' marked-for-deletion' : '');
                tr.innerHTML = `
                    <td class="${isMarkedForDeletion ? 'strikethrough' : ''}">${this.escapeHtml(metadata.filename)}</td>
                    <td>${this.formatFileSize(metadata.size)}</td>
                    <td>
                        <button type="button" class="remove-file-btn" data-file-key="${this.escapeHtml(fileKey)}" aria-label="${isMarkedForDeletion ? 'Undo deletion of' : 'Remove'} ${this.escapeHtml(metadata.filename)}">
                            ${isMarkedForDeletion ? '<img src="/static/img/undo.svg" alt="Undo">' : '<img src="/static/img/delete.svg" alt="Remove">'}
                        </button>
                    </td>
                `;
                existingFileListItems.appendChild(tr);

                // Attach remove button listener
                const removeBtn = tr.querySelector('.remove-file-btn');
                removeBtn.addEventListener('click', () => {
                    this.removeExistingFile(fileKey);
                });
            }
        }

        // Update new files list
        if (this.files.size === 0) {
            fileList.classList.add('d-none');
            if (this.existingFiles.size === 0) {
                return;
            }
        } else {
            fileList.classList.remove('d-none');
            fileListItems.innerHTML = '';

            for (const [fileId, file] of this.files) {
                const tr = document.createElement('tr');
                tr.className = 'file-list-item';
                tr.innerHTML = `
                    <td>${this.escapeHtml(file.name)}</td>
                    <td>${this.formatFileSize(file.size)}</td>
                    <td>
                        <button type="button" class="remove-file-btn" data-file-id="${fileId}" aria-label="Remove ${this.escapeHtml(file.name)}">
                            <img src="/static/img/delete.svg" alt="Remove">
                        </button>
                    </td>
                `;
                fileListItems.appendChild(tr);

                // Attach remove button listener
                const removeBtn = tr.querySelector('.remove-file-btn');
                removeBtn.addEventListener('click', () => {
                    this.removeFile(fileId);
                });
            }
        }

        // Update total size calculation (exclude files marked for deletion)
        const totalSize = this.getTotalSize();
        totalSizeElement.innerHTML = `<strong>Total:</strong> ${this.formatFileSize(totalSize)} / 5 MB`;
    }

    attachFilesToForm(form) {
        // Remove any existing file inputs we added
        const existingInputs = form.querySelectorAll('input[name="files"][data-widget-file], input[name="files_to_delete"][data-widget-file]');
        existingInputs.forEach(input => input.remove());

        // Create a new DataTransfer to hold our files
        const dt = new DataTransfer();
        for (const [fileId, file] of this.files) {
            dt.items.add(file);
        }

        // Create a new file input with all files
        if (this.files.size > 0) {
            const input = document.createElement('input');
            input.type = 'file';
            input.name = 'files';
            input.multiple = true;
            input.classList.add('d-none');
            input.setAttribute('data-widget-file', 'true');
            input.files = dt.files;
            form.appendChild(input);
        }

        // Add hidden inputs for files to delete
        for (const fileKey of this.filesToDelete) {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'files_to_delete';
            input.value = fileKey;
            input.setAttribute('data-widget-file', 'true');
            form.appendChild(input);
        }
    }

    getTotalSize() {
        let total = 0;
        // Add existing files size (excluding files marked for deletion)
        for (const [key, metadata] of this.existingFiles) {
            if (!this.filesToDelete.has(key)) {
                total += metadata.size;
            }
        }
        // Add new files size
        for (const [id, file] of this.files) {
            total += file.size;
        }
        return total;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    }

    getFileExtension(filename) {
        return '.' + filename.split('.').pop().toLowerCase();
    }

    showErrors(errors) {
        const errorsContainer = document.getElementById('uploadErrors');
        errorsContainer.classList.remove('d-none');
        errorsContainer.innerHTML = `
            <gcds-notice type="danger" notice-title-tag="h3" notice-title="Errors">
                <ul>
                    ${errors.map(error => `<li>${this.escapeHtml(error)}</li>`).join('')}
                </ul>
            </gcds-notice>
        `;
    }

    hideErrors() {
        const errorsContainer = document.getElementById('uploadErrors');
        errorsContainer.classList.add('d-none');
        errorsContainer.innerHTML = '';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the widget
document.addEventListener('DOMContentLoaded', () => {
    const uploadContainer = document.getElementById('fileUploadContainer');
    if (uploadContainer) {
        // Get options from data attributes
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
