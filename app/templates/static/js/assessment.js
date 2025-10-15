document.addEventListener('DOMContentLoaded', () => {

    // Initialize JSON upload widget for assessments
    const fileUploadContainer = document.getElementById('fileUploadContainer');
    if (fileUploadContainer) {
        const turndownService = new TurndownService({ headingStyle: 'atx', hr: '---', bulletListMarker: '-' });
        const fileUpload = new FileUploadWidget(fileUploadContainer, {
            singleFile: true,
            maxFileSize: 5 * 1024 * 1024,
            allowedExtensions: ['.json'],
            onFileLoaded: (content, file) => {
                try {
                    const jsonData = JSON.parse(content);
                    
                    // Validate structure
                    if (!jsonData.workspace || typeof jsonData.workspace !== 'object') {
                        throw new Error('Invalid JSON structure: missing workspace object');
                    }

                    const workspace = jsonData.workspace;

                    // Populate product name from workspace.name
                    if (workspace.name) {
                        const productNameInput = document.querySelector('[name="product_name"]');
                        if (productNameInput) {
                            productNameInput.value = workspace.name;
                            productNameInput.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    }

                    // Populate product description from workspace content
                    let description = '';
                    
                    if (workspace.application_information && workspace.application_information.content) {
                        description += workspace.application_information.content;
                    }

                    if (workspace.architecture && workspace.architecture.content) {
                        if (description) {
                            description += '\n\n';
                        }
                        description += workspace.architecture.content;
                    }

                    if (description) {
                        const productDescInput = document.querySelector('[name="product_description"]');
                        if (productDescInput) {
                            productDescInput.value = turndownService.turndown(description);
                            productDescInput.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    }

                } catch (error) {
                    console.error('Error parsing JSON:', error);
                    fileUpload.showErrors(['Invalid JSON file format or structure']);
                    fileUpload.clearAllFiles();
                }
            }
        });
    }
});