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
            await reloadPageContent();
        } else {
            console.error('Failed to delete item:', response.status);
        }
    } catch (error) {
        console.error('Error deleting item:', error);
    }
}

/**
 * Show a generic confirmation modal and wire up its controls.
 * The modal is assumed to exist in the DOM with IDs `confirmModal`,
 * `modalConfirm`, and `modalCancel`. When the confirm button is clicked
 * the provided callback is executed after the modal is hidden.
 *
 * @param {Function} onConfirm - Callback executed when the user confirms.
 * @returns {void}
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
 * Hide the confirmation modal and clear any attached event handlers.
 * This prevents leaked references to callbacks and ensures that the
 * modal can be reused safely.
 *
 * @returns {void}
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
 * Initialize event handlers and UI components after DOMContentLoaded.
 * Binds delete buttons to the confirmation flow, wires form change
 * events for evidence automation, initializes the compliance chart
 * and sliding panel components.
 *
 * @returns {void}
 */
document.addEventListener('DOMContentLoaded', function() {
    document.querySelector('#main-content').addEventListener('click', function(event) {
        const deleteBtn = event.target.closest && event.target.closest('.delete-item');
        if (deleteBtn) {
            event.preventDefault();
            const deleteUrl = deleteBtn.getAttribute('href');
            const csrfToken = deleteBtn.getAttribute('data-csrf-token');
            showConfirmModal(function() {
                deleteItem(deleteUrl, csrfToken);
            });
        }
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

/**
 * Reload the current page content and inject it into the #main-content element.
 * Also updates CSRF tokens across the entire page if present.
 *
 * @returns {Promise<void>}
 */
async function reloadPageContent() {
    try {
        const pageResponse = await fetch(window.location.pathname);
        if (pageResponse.ok) {
            const html = await pageResponse.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newContent = doc.querySelector('#main-content');
            const currentContent = document.querySelector('#main-content');
            
            if (newContent && currentContent) {
                currentContent.innerHTML = newContent.innerHTML;

                // Check if there are any CSRF tokens to update
                const csrfElement = newContent.querySelector('[data-csrf-token]');
                if (csrfElement) {
                    const csrfToken = csrfElement.getAttribute('data-csrf-token');
                    document.querySelectorAll('[data-csrf-token]').forEach((element) => {
                        element.setAttribute('data-csrf-token', csrfToken);
                    });
                }
            }
        }
    } catch (error) {
        console.error('Failed to reload page content:', error);
    }
}

/* 
 * Sliding panel behavior 
 *
 * Expected DOM structure:
 * - toggle button with id `sliding-panelToggle`
 * - panel container with id `sliding-panel`
 * - close control with id `sliding-panel-close`
 * - a `gcds-textarea` inside the panel that provides the prompt
 *
 * This function wires open/close actions, outside-click and Escape
 * behavior, and handles Enter-to-send for the embedded textarea.
 *
 * @returns {void}
 */
function initSlidingPanel() {
    const toggle = document.getElementById('sliding-panelToggle');
    const panel = document.getElementById('sliding-panel');
    const close = document.getElementById('sliding-panel-close');
    const prompt = panel ? panel.querySelector('gcds-textarea') : null;
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
}

/**
 * Chat client that manages a WebSocket connection to a chat backend and
 * handles streaming messages for an AI assistant UI.
 *
 * Options:
 * - maxReconnectAttempts: number (default: 3)
 * - reconnectDelay: number in ms (default: 3000)
 * - urlPath: path to the WebSocket endpoint (default: '/chat/ws')
 *
 * Properties exposed:
 * - isStreaming: boolean flag indicating streaming in progress
 * - sessionId: UUID for the current chat session
 */
class ChatClient {
    constructor(options = {}) {
        this.ws = null;
        this.isStreaming = false;
        this.currentAiMessage = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 3;
        this.reconnectDelay = options.reconnectDelay || 3000;
        this.urlPath = options.urlPath || '/chat/ws';
        this.markdown = null;
        this.buffer = '';
        this.sessionId = null;
        this.useWebSocket = typeof WebSocket !== 'undefined' && !window.location.href.includes('lambda-url');
        this.restEndpoint = options.restEndpoint || '/chat/response';
        this.elemClear = null;
        this.elemLoading = null;
        this.elemPrompt = null;
        this.elemSend = null;
    }

    /**
     * Whether the WebSocket is currently open or connecting.
     * @returns {boolean}
     */
    get isOpen() {
        return this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING);
    }

    /**
     * Initialize the WebSocket connection and set up event handlers.
     * If the client is disabled or already connecting/open it will no-op.
     * Reconnection is attempted up to `maxReconnectAttempts`.
     * Falls back to REST API if WebSocket is not supported.
     *
     * @returns {void}
     */
    init() {   
        this.markdown = window.markdownit();
        if (!this.sessionId) {
            this.sessionId = crypto.randomUUID();
        }

        // Bind event handlers
        this.elemClear = document.querySelector('#sliding-panel #clear-session');
        this.elemLoading = document.querySelector('#sliding-panel #loading');
        this.elemPrompt = document.querySelector('#sliding-panel gcds-textarea');
        this.elemSend = document.querySelector('#sliding-panel #send-message');

        this.elemClear.addEventListener('click', this.clearHandler.bind(this));
        this.elemPrompt.addEventListener('keydown', this.sendHandler.bind(this));
        this.elemSend.addEventListener('click', this.sendHandler.bind(this));
        

        if (!this.useWebSocket) {
            console.log('WebSocket not supported, using REST API');
            return;
        }

        if (this.isOpen) return;
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.warn('Max reconnect attempts reached, falling back to REST API');
            this.useWebSocket = false;
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${this.urlPath}`;        

        // Setup WebSocket
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
                    console.error('WebSocket authentication failed, falling back to REST API');
                    this.useWebSocket = false;
                    return;
                }

                if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                    setTimeout(() => this.init(), this.reconnectDelay);
                } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                    this.useWebSocket = false;
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        } catch (error) {
            console.error('Failed to create WebSocket, falling back to REST API:', error);
            this.useWebSocket = false;
        }
    }

    /**
     * Handle an incoming parsed WebSocket message payload.
     * Recognized types: 'start', 'chunk', 'end', 'error'.
     *
     * @param {Object} data - Parsed message object from the server.
     * @returns {void}
     */
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
                }
                break;
            case 'end':
                this.isStreaming = false;
                // Add action buttons if actions are present
                if (data.actions && data.actions.length > 0 && this.currentAiMessage) {
                    this.addActionButtons(this.currentAiMessage, data.actions);
                }
                this.currentAiMessage = null;
                console.log('Chat status: send finished');
                break;
            case 'error':
                this.isStreaming = false;
                this.addMessage(data.content || 'Sorry, I encountered an error. Please try again.', 'llm');
                console.log('Chat status: error');
                break;
        }
        const chatContainer = document.getElementById('llm-chat');
        if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    /**
     * Append a message bubble into the chat container.
     *
     * @param {string} message - Markdown-formatted message text.
     * @param {string} sender - Sender type, e.g. 'user' or 'llm'.
     * @returns {HTMLElement|null} The created message element or null if the container is missing.
     */
    addMessage(message, sender) {
        const chatContainer = document.getElementById('llm-chat');
        if (!chatContainer) return null;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}`;

        const bubble = document.createElement('div');
        bubble.className = 'bubble';

        bubble.innerHTML = DOMPurify.sanitize(this.markdown.render(message));

        messageDiv.appendChild(bubble);
        chatContainer.appendChild(messageDiv);

        chatContainer.scrollTop = chatContainer.scrollHeight;
        return messageDiv;
    }

    /**
     * Add action buttons to a message element.
     *
     * @param {HTMLElement} messageElement - The message div to add actions to.
     * @param {Array} actions - Array of action objects with label, description, action_type, and params.
     * @returns {void}
     */
    addActionButtons(messageElement, actions) {
        if (!messageElement || !actions || actions.length === 0) return;

        const actionsContainer = document.createElement('div');
        actionsContainer.className = 'chat-actions';

        actions.forEach((action) => {
            const button = document.createElement('button');
            button.className = 'chat-action-button';
            button.textContent = action.label;
            button.title = action.description;
            button.setAttribute('data-action-type', action.action_type);
            button.setAttribute('data-action-params', JSON.stringify(action.params));
            
            button.addEventListener('click', () => {
                this.executeAction(action.action_type, action.params);
            });

            actionsContainer.appendChild(button);
        });

        messageElement.appendChild(actionsContainer);
    }

    /**
     * Execute a chat action by calling the server endpoint.
     *
     * @param {string} actionType - The type of action to execute.
     * @param {Object} params - Parameters for the action.
     * @returns {Promise<void>}
     */
    async executeAction(actionType, params) {
        const panel = document.getElementById('sliding-panel');
        const csrfToken = panel ? panel.getAttribute('data-csrf-token') : '';

        if (!csrfToken) {
            this.addMessage('Error: Unable to execute action (missing CSRF token)', 'llm');
            return;
        }

        // Show feedback message
        this.addMessage('Applying...', 'user');

        try {
            const response = await fetch('/chat/action', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action_type: actionType,
                    params: params,
                    csrf_token: csrfToken
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to execute action');
            }

            const result = await response.json();
            this.addMessage(result.message || 'Action completed successfully', 'llm');

            await reloadPageContent();
        } catch (error) {
            console.error('Failed to execute action:', error);
            this.addMessage(`Error: ${error.message}`, 'llm');
        }
    }

    /**
     * Handle the send button click or Enter key press.
     * @param {*} event 
     * @returns {void} 
     */
    sendHandler(event) {
        if (event.type === 'click' || (event.key === 'Enter' && !event.shiftKey)) {
            event.preventDefault();
            const textarea = this.elemPrompt.shadowRoot.querySelector('textarea');
            const message = textarea ? textarea.value.trim() : '';
            if (!message || this.isStreaming) return;
            textarea.value = '';
            this.addMessage(message, 'user');
            this.send(message);
        }
    }

    /**
     * Send a message over the WebSocket. If the socket is not open the
     * message will be ignored and a warning will be logged.
     * Falls back to REST API if WebSocket is not available.
     *
     * @param {string} message - The plain-text message to send.
     * @returns {void}
     */
    async send(message) {
        if (!message || this.isStreaming) return;
        
        if (!this.sessionId) {
            this.sessionId = crypto.randomUUID();
        }

        if (!this.useWebSocket) {
            await this.sendViaRest(message);
            return;
        }

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify({ 
                    type: 'message', 
                    content: message,
                    current_page: document.querySelector('#main-content').innerHTML,
                    current_url: window.location.pathname,
                    session_id: this.sessionId
                }));
                console.log('Chat status: sending...');
            } catch (err) {
                console.error('Failed to send WebSocket message:', err);
            }
        } else {
            console.warn('WebSocket not open, falling back to REST API');
            await this.sendViaRest(message);
        }
    }

    /**
     * Send a message via REST API and simulate streaming by processing the response.
     *
     * @param {string} message - The plain-text message to send.
     * @returns {Promise<void>}
     */
    async sendViaRest(message) {
        this.isStreaming = true;
        this.buffer = '';
        this.currentAiMessage = this.addMessage('', 'llm');
        this.elemLoading.classList.add('show');

        try {
            const response = await fetch(this.restEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId,
                    current_page: document.querySelector('#main-content') ? document.querySelector('#main-content').innerHTML : '',
                    current_url: window.location.pathname
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error: ${response.status}`);
            }

            const data = await response.json();
            
            if (this.currentAiMessage) {
                const bubble = this.currentAiMessage.querySelector('.bubble');
                bubble.innerHTML = DOMPurify.sanitize(this.markdown.render(data.message || ''));
                
                // Add action buttons if actions are present
                if (data.actions && data.actions.length > 0) {
                    this.addActionButtons(this.currentAiMessage, data.actions);
                }
                
                const chatContainer = document.getElementById('llm-chat');
                if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            this.isStreaming = false;
            this.currentAiMessage = null;
            console.log('Chat status: send finished (REST)');
        } catch (err) {
            console.error('Failed to send REST message:', err);
            this.isStreaming = false;
            this.addMessage('Sorry, I encountered an error. Please try again.', 'llm');
        } finally {
            this.elemLoading.classList.remove('show');
        }
    }

    /**
     * Close the WebSocket and reset streaming state.
     *
     * @param {boolean} [graceful=true] - If true, attempt a graceful close with code 1000.
     * @returns {void}
     */
    close(graceful = true) {
        try {
            if (this.ws && this.useWebSocket) {
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

    /**
     * Reset the internal session state for the chat client. Does not
     * close the WebSocket.
     *
     * @returns {void}
     */
    resetSession() {
        this.sessionId = null;
        this.buffer = '';
        this.currentAiMessage = null;
        this.isStreaming = false;
    }

    clearHandler(event) {
        event.preventDefault();
        this.resetSession();
        this.clearMessages();
        this.elemPrompt.focus();
    }

    /**
     * Remove all messages from the UI chat container.
     *
     * @returns {void}
     */
    clearMessages() {
        const chatContainer = document.getElementById('llm-chat');
        if (chatContainer) {
            chatContainer.innerHTML = '';
        }
    }
}
const chatClient = new ChatClient();


