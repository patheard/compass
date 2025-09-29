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
        initWebSocketChat();
    }

    function closePanel(e) {
        if (e) e.preventDefault();
        panel.classList.remove('open');
        panel.setAttribute('aria-hidden', 'true');
        toggle.setAttribute('aria-expanded', 'false');

        // Clean up WebSocket when panel is closed. Do NOT permanently disable
        // websockets (useWebSocket) so users can reopen the panel and reconnect.
        try {
            if (chatWebSocket) {
                // Close the socket gracefully if open/connecting. This will
                // trigger onclose but since we null it below reconnect logic
                // will create a fresh socket on next open.
                if (chatWebSocket.readyState === WebSocket.OPEN || chatWebSocket.readyState === WebSocket.CONNECTING) {
                    try {
                        chatWebSocket.close(1000, 'Panel closed');
                    } catch (closeErr) {
                        console.debug('Error while closing WebSocket:', closeErr);
                    }
                }

                // Reset the socket reference so initWebSocketChat can create a new one
                chatWebSocket = null;
                // Reset reconnect attempts so user gets full retry budget on reopen
                reconnectAttempts = 0;
            }
        } catch (err) {
            console.error('Error cleaning up WebSocket on panel close:', err);
        }

        // Reset streaming/UI state to avoid stale loaders or partial messages
        isStreaming = false;
        currentAiMessage = null;
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
    prompt.addEventListener('keydown', handleChatKeydown);
}

// WebSocket chat functionality
let chatWebSocket = null;
let isStreaming = false;
let currentAiMessage = null;
let useWebSocket = true;
let reconnectAttempts = 0;
let maxReconnectAttempts = 3;
let reconnectDelay = 3000; // 3 seconds
const markdown = window.markdownit();

/**
 * Initialize WebSocket connection for chat
 */
function initWebSocketChat() {
    // If an existing socket is present and still open/connecting, do nothing
    if (chatWebSocket && (chatWebSocket.readyState === WebSocket.OPEN || chatWebSocket.readyState === WebSocket.CONNECTING)) {
        console.log('WebSocket already initialized');
        return;
    }

    // Don't try to reconnect if we've exceeded max attempts
    if (reconnectAttempts >= maxReconnectAttempts) {
        console.warn('Max reconnect attempts reached, using REST API only');
        useWebSocket = false;
        return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/chat/ws`;
    
    try {
        chatWebSocket = new WebSocket(wsUrl);
        chatWebSocket.onopen = function() {
            console.log('WebSocket connected');
            console.log('Chat status: connected');
            reconnectAttempts = 0;
        };
        
        chatWebSocket.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };
        
        chatWebSocket.onclose = function(event) {
            console.log('WebSocket disconnected:', event.code, event.reason);
            console.log('Chat status: disconnected');
            
            // Handle different close codes
            if (event.code === 1008) {
                // Authentication failed
                console.error('WebSocket authentication failed');
                useWebSocket = false;
                console.log('Chat status: authentication failed');
                return;
            }
            
            // Try to reconnect after a delay if it wasn't a clean close
            if (event.code !== 1000 && useWebSocket && reconnectAttempts < maxReconnectAttempts) {
                reconnectAttempts++;
                console.log(`Chat status: reconnecting... (${reconnectAttempts}/${maxReconnectAttempts})`);
                setTimeout(() => {
                    console.log(`Attempting to reconnect WebSocket... (${reconnectAttempts}/${maxReconnectAttempts})`);
                    initWebSocketChat();
                }, reconnectDelay);
            } else if (reconnectAttempts >= maxReconnectAttempts) {
                useWebSocket = false;
                console.log('Chat status: max reconnect attempts reached');
            }
        };
        
        chatWebSocket.onerror = function(error) {
            console.error('WebSocket error:', error);
            console.log('Chat status: connection error');
        };
        
    } catch (error) {
        console.error('Failed to create WebSocket:', error);
        useWebSocket = false;
        console.log('Chat status: failed to create WebSocket');
    }
}

/**
 * Handle WebSocket messages
 */
let buffer = '';
function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'start':
            buffer = '';
            isStreaming = true;
            currentAiMessage = addChatMessage('', 'llm');
            break;
            
        case 'chunk':
            if (currentAiMessage) {
                buffer += data.content;
                const bubble = currentAiMessage.querySelector('.bubble');
                bubble.innerHTML = DOMPurify.sanitize(markdown.render(buffer));
                const chatContainer = document.getElementById('llmChat');
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            break;
            
        case 'end':
            isStreaming = false;
            currentAiMessage = null;
            console.log('Chat status: send finished');
            break;
            
        case 'error':
            isStreaming = false;
            addChatMessage(data.content || 'Sorry, I encountered an error. Please try again.', 'llm');
            console.log('Chat status: error');
            break;
    }
}

/**
 * Handle keydown events for the chat textarea
 */
function handleChatKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendChatMessage();
    }
}

/**
 * Send a chat message via WebSocket
 */
async function sendChatMessage() {
    const prompt = document.querySelector('#sliding-panel gcds-textarea');
    const chatContainer = document.getElementById('llmChat');
    
    if (!prompt || !chatContainer) return;
    
    const textarea = prompt.shadowRoot.querySelector('textarea');
    const message = textarea.value.trim();
    
    if (!message || isStreaming) return;
    textarea.value = '';
    
    addChatMessage(message, 'user');
    
    if (useWebSocket && chatWebSocket && chatWebSocket.readyState === WebSocket.OPEN) {
        sendMessageViaWebSocket(message);
    }
}

/**
 * Send message via WebSocket
 */
function sendMessageViaWebSocket(message) {
    try {
        chatWebSocket.send(JSON.stringify({
            type: 'message',
            content: message
        }));
        console.log('Chat status: sending...');
    } catch (error) {
        console.error('Failed to send WebSocket message:', error);
    }
}

/**
 * Add a message to the chat container
 */
function addChatMessage(message, sender) {
    const chatContainer = document.getElementById('llmChat');
    if (!chatContainer) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    // Convert newlines to <br> for proper display
    bubble.innerHTML = message.replace(/\n/g, '<br>');
    
    messageDiv.appendChild(bubble);
    chatContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;

    return messageDiv
}

