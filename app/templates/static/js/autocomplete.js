/**
 * Autocomplete Component
 * Provides autocomplete functionality for item selection with badge display.
 * Expects items as an array of objects with {value, label} properties.
 */
class Autocomplete {
    constructor(element, items) {
        this.input = element;
        if (!this.input) return;

        this.allItems = items || [];
        this.selectedItems = new Map(); // Map value -> label
        this.dropdown = null;
        this.badgeContainer = null;
        this.hiddenInput = null;

        this.init();
    }

    init() {
        // Create dropdown element
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'autocomplete-dropdown';
        this.dropdown.style.display = 'none';

        // Create badge container
        this.badgeContainer = document.createElement('div');
        this.badgeContainer.className = 'autocomplete-badges';

        // Create hidden input for form submission
        this.hiddenInput = document.createElement('input');
        this.hiddenInput.type = 'hidden';
        this.hiddenInput.name = this.input.getAttribute('name').replace('_autocomplete', '');

        // Insert elements after the input
        this.input.parentNode.insertBefore(this.badgeContainer, this.input.nextSibling);
        this.input.parentNode.insertBefore(this.dropdown, this.input.nextSibling);
        this.input.parentNode.insertBefore(this.hiddenInput, this.dropdown.nextSibling);

        // Bind events
        this.input.addEventListener('input', this.handleInput.bind(this));
        this.input.addEventListener('focus', this.handleFocus.bind(this));
        this.input.addEventListener('keydown', this.handleKeydown.bind(this));
        document.addEventListener('click', this.handleClickOutside.bind(this));

        // Load pre-selected items and update hidden input with the current items
        this.loadPreselectedItems();
        this.updateHiddenInput();
    }

    loadPreselectedItems() {
        // Look for pre-selected items in data attribute
        const preselected = this.input.getAttribute('data-selected');
        if (preselected) {
            try {
                const items = JSON.parse(preselected);
                items.forEach(item => {
                    if (typeof item === 'object' && item.value && item.label) {
                        this.addItem(item, false);
                    }
                });
            } catch (e) {
                console.error('Failed to parse preselected items:', e);
            }
        }
    }

    handleInput(event) {
        const value = event.target.value.trim().toLowerCase();
        this.filterItems(value);
    }

    handleFocus() {
        if (this.input.value) {
            this.filterItems(this.input.value.trim().toLowerCase());
        }
    }

    handleKeydown(event) {
        if (event.key === 'Escape') {
            this.hideDropdown();
        } else if (event.key === 'Enter') {
            event.preventDefault();
            const firstOption = this.dropdown.querySelector('.autocomplete-option');
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

    filterItems(query) {
        const filtered = this.allItems.filter(item => {
            const labelMatch = item.label && item.label.toLowerCase().includes(query);
            const valueMatch = item.value && item.value.toLowerCase().includes(query);
            return (labelMatch || valueMatch) && !this.selectedItems.has(item.value);
        });

        if (filtered.length === 0) {
            this.hideDropdown();
            return;
        }

        this.showDropdown(filtered);
    }

    showDropdown(items) {
        this.dropdown.innerHTML = '';
        
        items.forEach(item => {
            const option = document.createElement('div');
            option.className = 'autocomplete-option';
            option.textContent = item.label || item.value;
            option.addEventListener('click', () => {
                this.addItem(item);
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

    addItem(item, updateInput = true) {
        const value = typeof item === 'object' ? item.value : item;
        const label = typeof item === 'object' ? item.label : item;
        
        if (this.selectedItems.has(value)) return;

        this.selectedItems.set(value, label);
        this.renderBadges();
        
        if (updateInput) {
            this.updateHiddenInput();
        }
    }

    removeItem(value) {
        this.selectedItems.delete(value);
        this.renderBadges();
        this.updateHiddenInput();
    }

    renderBadges() {
        this.badgeContainer.innerHTML = '';
        
        this.selectedItems.forEach((label, value) => {
            const badge = document.createElement('span');
            badge.className = 'autocomplete-badge';
            badge.innerHTML = `
                ${label}
                <button type="button" class="badge-remove" aria-label="Remove ${label}" title="Remove ${label}">
                    ×
                </button>
            `;
            
            const removeBtn = badge.querySelector('.badge-remove');
            removeBtn.addEventListener('click', () => this.removeItem(value));
            
            this.badgeContainer.appendChild(badge);
        });
    }

    updateHiddenInput() {
        // Store as JSON array of values for backend processing
        this.hiddenInput.value = JSON.stringify([...this.selectedItems.keys()]);
    }
}

/**
 * Initialize autocomplete on form pages
 */
document.addEventListener('DOMContentLoaded', function() {
    const autocompleteInputs = document.querySelectorAll('[data-autocomplete]');
    autocompleteInputs.forEach(input => {
        const itemsData = input.getAttribute('data-items');
        if (itemsData) {
            try {
                const items = JSON.parse(itemsData);
                new Autocomplete(input, items);
            } catch (e) {
                console.error('Failed to initialize autocomplete:', e);
            }
        }
    });
});