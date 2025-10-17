/**
 * Generic tab switcher
 * 
 * Usage:
 * 1. Add data-tabs attribute to the nav element containing tabs
 * 2. Add data-tab-link attribute to each tab link with href="#panel-id"
 * 3. Add data-tab-panel attribute to each content panel with matching id
 * 4. Set aria-current="page" on the initially active tab
 * 5. Add hidden attribute to initially hidden panels
 */
(function() {
    'use strict';

    /**
     * Initialize tabs functionality
     */
    function initTabs() {
        const tabContainers = document.querySelectorAll('[data-tabs]');
        
        tabContainers.forEach(function(container) {
            const tabLinks = container.querySelectorAll('[data-tab-link]');
            
            tabLinks.forEach(function(link) {
                link.addEventListener('click', function(event) {
                    event.preventDefault();
                    
                    const targetId = this.getAttribute('href').substring(1);
                    const targetPanel = document.getElementById(targetId);
                    
                    if (!targetPanel) {
                        return;
                    }
                    
                    // Update tab link states
                    tabLinks.forEach(function(tab) {
                        tab.removeAttribute('aria-current');
                    });
                    this.setAttribute('aria-current', 'page');
                    
                    // Update panel visibility
                    const allPanels = document.querySelectorAll('[data-tab-panel]');
                    allPanels.forEach(function(panel) {
                        panel.setAttribute('hidden', '');
                    });
                    targetPanel.removeAttribute('hidden');
                });
            });
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTabs);
    } else {
        initTabs();
    }
})();
