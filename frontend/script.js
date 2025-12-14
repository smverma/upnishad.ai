const chatHistory = document.getElementById('chat-history');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const dailyStoryBtn = document.getElementById('daily-story-btn');
const suggestionChips = document.querySelectorAll('.suggestion-chip');

function formatMessage(text) {
    // Escape HTML first to prevent injection if it was user content, 
    // but here we trust the backend mostly. Ideally use a library.
    // Simple bold parser
    let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Handle newlines: \n\n becomes paragraph break, \n becomes <br>
    // But since we use pre-wrap, \n works. 
    // To strict "leave one line", \n\n is enough with pre-wrap.
    // However, user specifically asked for "leave one line".
    // Let's ensure \n\n maps to TWO lines of space.
    // Actually, converting to <p> is safer for spacing control.

    // Split by double newlines to find paragraphs
    const paragraphs = formatted.split(/\n\n+/);
    if (paragraphs.length > 1) {
        return paragraphs.map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
    }

    // Fallback if no paragraphs
    return formatted.replace(/\n/g, '<br>');
}

function addMessage(text, isUser) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message');
    msgDiv.classList.add(isUser ? 'user-message' : 'bot-message');

    if (isUser) {
        msgDiv.textContent = text;
    } else {
        // Parse markdown for bot
        msgDiv.innerHTML = formatMessage(text);
    }

    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    addMessage(text, true);
    userInput.value = '';

    try {
        const response = await fetch('/api/ask?question=' + encodeURIComponent(text), {
            method: 'POST'
        });
        if (!response.ok) {
            const errText = await response.text(); // Try to get text if not JSON
            try {
                const errJson = JSON.parse(errText);
                throw new Error(errJson.answer || `Server Error: ${response.status}`);
            } catch (e) {
                throw new Error(`Server Error: ${response.status} - ${errText}`);
            }
        }
        const data = await response.json();
        addMessage(data.answer, false);
    } catch (error) {
        addMessage(`Sorry, trouble connecting: ${error.message}`, false);
        console.error(error);
    }
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

suggestionChips.forEach(chip => {
    chip.addEventListener('click', () => {
        userInput.value = chip.textContent;
        sendMessage();
    });
});

dailyStoryBtn.addEventListener('click', async () => {
    dailyStoryBtn.disabled = true;
    dailyStoryBtn.textContent = "Generating...";
    try {
        await fetch('/api/trigger-daily-story', { method: 'POST' });
        alert("Daily story generation triggered! Check the logs/output.");
    } catch (error) {
        console.error(error);
        alert("Failed to trigger story.");
    } finally {
        dailyStoryBtn.disabled = false;
        dailyStoryBtn.textContent = "Generate Daily Wisdom";
    }
});
