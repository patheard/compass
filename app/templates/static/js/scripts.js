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
    // Also listen for job template changes to autofill title/description
    const jobTemplateSelect = document.querySelector('[name="job_template_id"]');
    if (jobTemplateSelect) {
        jobTemplateSelect.addEventListener('change', updateEvidenceWithJobTemplate);
    }

    // Initialize components
    initComplianceChart();
    initSlidingPanel();
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
 * When a job template is selected, find the hidden div[data-id] with the same id
 * and copy its data-name and data-description into the title and description fields.
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

/*
 * Initialize the compliance chart
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

/* 
 * Sliding panel behavior 
 */
function initSlidingPanel() {
    const toggle = document.getElementById('sliding-panelToggle');
    const panel = document.getElementById('sliding-panel');
    const close = document.getElementById('sliding-panel-close');
    const prompt = panel.querySelector('gcds-textarea');
    if (!toggle || !panel || !close || !prompt) return;

    function openPanel(e) {
        if (e) e.preventDefault();
        panel.classList.add('open');
        panel.setAttribute('aria-hidden', 'false');
        toggle.setAttribute('aria-expanded', 'true');
        prompt.focus();
        prompt.shadowRoot.querySelector('textarea').setAttribute('placeholder', prompt.getAttribute('data-placeholder'));
        chatClient.init();
    }

    function closePanel(e) {
        if (e) e.preventDefault();
        panel.classList.remove('open');
        panel.setAttribute('aria-hidden', 'true');
        toggle.setAttribute('aria-expanded', 'false');
        chatClient.close(true);
    }

    toggle.addEventListener('click', openPanel);
    close.addEventListener('click', closePanel);

    document.addEventListener('click', function(e) {
        if (!panel.classList.contains('open')) return;
        const target = e.target;
        if (panel.contains(target) || toggle.contains(target)) return;
        closePanel(e);
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && panel.classList.contains('open')) {
            closePanel();
        }
    });

    // Add Enter key handler for chat
    prompt.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            const textarea = prompt.shadowRoot.querySelector('textarea');
            const message = textarea ? textarea.value.trim() : '';
            if (!message || chatClient.isStreaming) return;
            textarea.value = '';
            chatClient.addMessage(message, 'user');
            chatClient.send(message);
        }
    });
}

class ChatClient {
    constructor(options = {}) {
        this.ws = null;
        this.isStreaming = false;
        this.currentAiMessage = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 3;
        this.reconnectDelay = options.reconnectDelay || 3000;
        this.urlPath = options.urlPath || '/chat/ws';
        this.enabled = true;
        this.markdown = null;
    }

    get isOpen() {
        return this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING);
    }

    init() {
        if (!this.enabled) return;
        if (this.isOpen) return;
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.warn('Max reconnect attempts reached, disabling WebSocket');
            this.enabled = false;
            return;
        }

        this.markdown = window.markdownit();
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${this.urlPath}`;

        try {
            this.ws = new WebSocket(wsUrl);
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (err) {
                    console.error('Failed to parse WebSocket message:', err);
                }
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);

                if (event.code === 1008) {
                    // Authentication failed; stop reconnecting
                    console.error('WebSocket authentication failed');
                    this.enabled = false;
                    return;
                }

                if (event.code !== 1000 && this.enabled && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                    setTimeout(() => this.init(), this.reconnectDelay);
                } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                    this.enabled = false;
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.enabled = false;
        }
    }

    handleMessage(data) {
        switch (data.type) {
            case 'start':
                this.buffer = '';
                this.isStreaming = true;
                this.currentAiMessage = this.addMessage('', 'llm');
                break;
            case 'chunk':
                if (this.currentAiMessage) {
                    this.buffer += data.content;
                    const bubble = this.currentAiMessage.querySelector('.bubble');
                    bubble.innerHTML = DOMPurify.sanitize(this.markdown.render(this.buffer));
                    const chatContainer = document.getElementById('llmChat');
                    if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
                }
                break;
            case 'end':
                this.isStreaming = false;
                this.currentAiMessage = null;
                console.log('Chat status: send finished');
                break;
            case 'error':
                this.isStreaming = false;
                this.addMessage(data.content || 'Sorry, I encountered an error. Please try again.', 'llm');
                console.log('Chat status: error');
                break;
        }
    }

    /**
     * Add a message to the chat container
     * Returns the created message element (useful for streaming updates)
     */
    addMessage(message, sender) {
        const chatContainer = document.getElementById('llmChat');
        if (!chatContainer) return null;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}`;

        const bubble = document.createElement('div');
        bubble.className = 'bubble';

        // Convert newlines to <br> for proper display
        bubble.innerHTML = (message || '').replace(/\n/g, '<br>');

        messageDiv.appendChild(bubble);
        chatContainer.appendChild(messageDiv);

        // Scroll to bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;

        return messageDiv;
    }

    send(message) {
        if (!message || this.isStreaming) return;
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify({ type: 'message', content: message }));
                console.log('Chat status: sending...');
            } catch (err) {
                console.error('Failed to send WebSocket message:', err);
            }
        } else {
            console.warn('WebSocket not open, message not sent');
        }
    }

    close(graceful = true) {
        try {
            if (this.ws) {
                if (graceful && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
                    try { this.ws.close(1000, 'Panel closed'); } catch (e) { /* ignore */ }
                }
                this.ws = null;
            }
        } catch (err) {
            console.error('Error closing WebSocket:', err);
        }
        this.isStreaming = false;
        this.currentAiMessage = null;
        this.reconnectAttempts = 0;
    }
}
const chatClient = new ChatClient();
