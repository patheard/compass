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
     * Switch to a specific tab
     */
    function switchToTab(targetId) {
        const targetPanel = document.getElementById(targetId);
        if (!targetPanel) {
            return;
        }
        
        const tabLink = document.querySelector('[data-tab-link][href="#' + targetId + '"]');
        if (!tabLink) {
            return;
        }
        
        // Find the tab container
        const container = tabLink.closest('[data-tabs]');
        if (!container) {
            return;
        }
        
        // Update tab link states within this container
        const tabLinks = container.querySelectorAll('[data-tab-link]');
        tabLinks.forEach(function(tab) {
            tab.removeAttribute('aria-current');
        });
        tabLink.setAttribute('aria-current', 'page');
        
        // Update panel visibility
        const allPanels = document.querySelectorAll('[data-tab-panel]');
        allPanels.forEach(function(panel) {
            panel.setAttribute('hidden', '');
        });
        targetPanel.removeAttribute('hidden');
    }

    /**
     * Handle tab click event
     */
    function handleTabClick(event) {
        const tabLink = event.target.closest('[data-tab-link]');
        if (!tabLink) {
            return;
        }
    }

    /**
     * Handle hash changes (from clicks or back/forward navigation)
     */
    function handleHashChange() {
        const hash = window.location.hash;
        if (hash) {
            const targetId = hash.substring(1);
            switchToTab(targetId);
        }
    }

    // Use event delegation on document to handle dynamically loaded tabs
    document.addEventListener('click', handleTabClick);
    
    // Handle hash changes (including back/forward navigation)
    window.addEventListener('hashchange', handleHashChange);
    
    // Handle initial hash on page load
    if (window.location.hash) {
        handleHashChange();
    }
})();
