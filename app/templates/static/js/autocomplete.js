/**
 * AWS Resources Autocomplete Component
 * Provides autocomplete functionality for AWS resource selection with badge display.
 * Expects resources as an array of objects with {value, label} properties.
 */
class AwsResourcesAutocomplete {
    constructor(element, resources) {
        this.input = element;
        if (!this.input) return;

        this.allResources = resources || [];
        this.selectedResources = new Map(); // Map value -> label
        this.dropdown = null;
        this.badgeContainer = null;
        this.hiddenInput = null;

        this.init();
    }

    init() {
        // Create dropdown element
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'aws-autocomplete-dropdown';
        this.dropdown.style.display = 'none';

        // Create badge container
        this.badgeContainer = document.createElement('div');
        this.badgeContainer.className = 'aws-resource-badges';

        // Create hidden input for form submission
        this.hiddenInput = document.createElement('input');
        this.hiddenInput.type = 'hidden';
        this.hiddenInput.name = 'aws_resources';

        // Insert elements after the input
        this.input.parentNode.insertBefore(this.badgeContainer, this.input.nextSibling);
        this.input.parentNode.insertBefore(this.dropdown, this.input.nextSibling);
        this.input.parentNode.insertBefore(this.hiddenInput, this.dropdown.nextSibling);

        // Bind events
        this.input.addEventListener('input', this.handleInput.bind(this));
        this.input.addEventListener('focus', this.handleFocus.bind(this));
        this.input.addEventListener('keydown', this.handleKeydown.bind(this));
        document.addEventListener('click', this.handleClickOutside.bind(this));

        // Load pre-selected resources and update hidden input with the current resources
        this.loadPreselectedResources();
        this.updateHiddenInput();
    }

    loadPreselectedResources() {
        // Look for pre-selected resources in data attribute
        const preselected = this.input.getAttribute('data-selected');
        if (preselected) {
            try {
                const resources = JSON.parse(preselected);
                resources.forEach(resource => {
                    if (typeof resource === 'object' && resource.value && resource.label) {
                        this.addResource(resource, false);
                    }
                });
            } catch (e) {
                console.error('Failed to parse preselected resources:', e);
            }
        }
    }

    handleInput(event) {
        const value = event.target.value.trim().toLowerCase();
        this.filterResources(value);
    }

    handleFocus() {
        if (this.input.value) {
            this.filterResources(this.input.value.trim().toLowerCase());
        }
    }

    handleKeydown(event) {
        if (event.key === 'Escape') {
            this.hideDropdown();
        } else if (event.key === 'Enter') {
            event.preventDefault();
            const firstOption = this.dropdown.querySelector('.aws-autocomplete-option');
            if (firstOption && this.dropdown.style.display !== 'none') {
                firstOption.click();
            }
        }
    }

    handleClickOutside(event) {
        if (!this.input.contains(event.target) && !this.dropdown.contains(event.target)) {
            this.hideDropdown();
        }
    }

    filterResources(query) {
        const filtered = this.allResources.filter(resource => {
            const labelMatch = resource.label && resource.label.toLowerCase().includes(query);
            const valueMatch = resource.value && resource.value.toLowerCase().includes(query);
            return (labelMatch || valueMatch) && !this.selectedResources.has(resource.value);
        });

        if (filtered.length === 0) {
            this.hideDropdown();
            return;
        }

        this.showDropdown(filtered);
    }

    showDropdown(resources) {
        this.dropdown.innerHTML = '';
        
        resources.forEach(resource => {
            const option = document.createElement('div');
            option.className = 'aws-autocomplete-option';
            option.textContent = resource.label || resource.value;
            option.addEventListener('click', () => {
                this.addResource(resource);
                this.input.value = '';
                this.hideDropdown();
                this.input.focus();
            });
            this.dropdown.appendChild(option);
        });

        this.dropdown.style.display = 'block';
    }

    hideDropdown() {
        this.dropdown.style.display = 'none';
    }

    addResource(resource, updateInput = true) {
        const value = typeof resource === 'object' ? resource.value : resource;
        const label = typeof resource === 'object' ? resource.label : resource;
        
        if (this.selectedResources.has(value)) return;

        this.selectedResources.set(value, label);
        this.renderBadges();
        
        if (updateInput) {
            this.updateHiddenInput();
        }
    }

    removeResource(value) {
        this.selectedResources.delete(value);
        this.renderBadges();
        this.updateHiddenInput();
    }

    renderBadges() {
        this.badgeContainer.innerHTML = '';
        
        this.selectedResources.forEach((label, value) => {
            const badge = document.createElement('span');
            badge.className = 'aws-resource-badge';
            badge.innerHTML = `
                ${label}
                <button type="button" class="badge-remove" aria-label="Remove ${label}" title="Remove ${label}">
                    ×
                </button>
            `;
            
            const removeBtn = badge.querySelector('.badge-remove');
            removeBtn.addEventListener('click', () => this.removeResource(value));
            
            this.badgeContainer.appendChild(badge);
        });
    }

    updateHiddenInput() {
        // Store as JSON array of values for backend processing
        this.hiddenInput.value = JSON.stringify([...this.selectedResources.keys()]);
    }
}

/**
 * Initialize AWS resources autocomplete on form pages
 */
document.addEventListener('DOMContentLoaded', function() {
    const awsResourceInput = document.querySelector('[name="aws_resources_autocomplete"]');
    if (awsResourceInput) {
        const resourcesData = awsResourceInput.getAttribute('data-resources');
        if (resourcesData) {
            try {
                const resources = JSON.parse(resourcesData);
                new AwsResourcesAutocomplete(awsResourceInput, resources);
            } catch (e) {
                console.error('Failed to initialize AWS resources autocomplete:', e);
            }
        }
    }
});