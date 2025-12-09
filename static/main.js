// --- New Utility Functions ---

function showLoading() {
    document.getElementById('loading-indicator').style.display = 'block';
    document.getElementById('send-button').disabled = true;
    document.getElementById('clear-button').disabled = true;
}

function hideLoading() {
    document.getElementById('loading-indicator').style.display = 'none';
    document.getElementById('send-button').disabled = false;
    document.getElementById('clear-button').disabled = false;
}

function autoScroll() {
    const chatHistory = document.getElementById('chat-history');
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function clearChat() {
    document.getElementById('chat-history').innerHTML = '';
    console.log("Chat history cleared.");
}


// --- Core Chat Logic ---

function appendMessage(sender, message, sources = '', mode = '') {
    const chatHistory = document.getElementById('chat-history');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${sender}-message`);

    let content = message;

    // Add source and mode information for the bot's response
    if (sender === 'bot') {
        let sourceInfo = '';
        if (mode) {
            sourceInfo += `<strong>Mode:</strong> ${mode}`;
        }
        if (sources) {
            sourceInfo += (mode ? ' | ' : '') + `<strong>Sources:</strong> ${sources}`;
        }
        
        // Append source info below the main answer
        if (sourceInfo) {
            content += `<div class="source-info">${sourceInfo}</div>`;
        }
    }

    messageDiv.innerHTML = content;
    chatHistory.appendChild(messageDiv);
}


async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const message = userInput.value.trim();

    if (message === '') return;
    // Get the selected mode
    const modeSelect = document.getElementById("mode-select");
    const mode = modeSelect ? modeSelect.value : "chat";

    // 1. Append user message and clear input
    appendMessage('user', message);
    userInput.value = '';
    
    showLoading();
    autoScroll(); // Scroll after user message is added

    try {
        // Use the hybrid route (assuming it's mapped to /answer or /hybridanswer)
        const response = await fetch('/chat', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                message: message,
                mode: mode 
            }),
        });

        const data = await response.json();
        
        if (data.error) {
            // 4. Implement robust error handling
            appendMessage('bot', `An error occurred: ${data.error}`, '', 'Error');
        } else {
            // 2. Append bot message with sources and mode
            const sources = data.sources || '';
            const mode = data.mode || 'General Chat'; // Default to General Chat if mode is missing
            appendMessage('bot', data.answer, sources, mode);
        }
    } catch (error) {
        // 4. Implement robust error handling for network/fetch errors
        console.error('Fetch Error:', error);
        appendMessage('bot', `Network error: Could not connect to the server.`, '', 'Error');
    } finally {
        hideLoading();
        autoScroll(); // Scroll again after bot message is added
    }
}
/**
 * Auto-scrolls the chat window to the bottom to show the latest message.
 */
function autoScroll() {
    const chatHistory = document.getElementById('chat-history');
    // Set the scroll position to the total height of the scrollable content
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

/**
 * Clears all messages from the chat history container.
 */
function clearChat() {
    const chatHistory = document.getElementById('chat-history');
    chatHistory.innerHTML = ''; // Clears all inner HTML content
    console.log("Chat history cleared.");
    // Optionally, send a cleanup message to the server to reset memory (for US-01)
    // For now, we'll just clear the visual history.
}
