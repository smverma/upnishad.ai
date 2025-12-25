document.addEventListener('DOMContentLoaded', () => {
    const chatHistory = document.getElementById('chat-history');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const suggestionChipsContainer = document.querySelector('.suggestions-container');
    const loadingOverlay = document.getElementById('loading-overlay');

    // HARDCODED MODE
    const currentMode = "deep_dive";

    function toggleLoading(show) {
        if (!loadingOverlay) return;
        if (show) {
            loadingOverlay.classList.remove('hidden');
        } else {
            loadingOverlay.classList.add('hidden');
        }
    }

    function formatMessage(text) {
        if (!text) return "";
        let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        const paragraphs = formatted.split(/\n\n+/);
        if (paragraphs.length > 1) {
            return paragraphs.map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
        }
        return formatted.replace(/\n/g, '<br>');
    }

    function addMessage(text, isUser) {
        if (!chatHistory) return;
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message');
        msgDiv.classList.add(isUser ? 'user-message' : 'bot-message');

        if (isUser) {
            msgDiv.textContent = text;
        } else {
            // Check if it looks like our internal HTML format (deep dive styling)
            if (typeof text === 'string' && (text.trim().startsWith('<div') || text.includes('deep-dive-content'))) {
                msgDiv.innerHTML = text;
            } else {
                msgDiv.innerHTML = formatMessage(text);
            }
        }

        chatHistory.appendChild(msgDiv);
        setTimeout(() => {
            msgDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 50);
    }

    async function sendMessage() {
        if (!userInput) return;
        const text = userInput.value.trim();
        if (!text) return;

        addMessage(text, true);
        userInput.value = '';

        toggleLoading(true);

        try {
            // STRICTLY USE DEEP DIVE MODE
            console.log("Sending Deep Dive Request...");
            const response = await fetch(`/api/ask?question=${encodeURIComponent(text)}&mode=${currentMode}`, {
                method: 'POST'
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`Server Error: ${response.status} - ${errText}`);
            }

            const data = await response.json();
            console.log("Response Data:", data);

            let answerText = "";
            let followUps = [];

            // Robust JSON Parsing/Unwrapping
            if (data.answer && data.answer.answer) {
                answerText = data.answer.answer;
                followUps = data.answer.follow_up_questions || [];
            } else if (data.answer) {
                answerText = data.answer;
            }

            // Wrap in styling for emphasis
            answerText = `<div class="deep-dive-content" style="border-left: 3px solid #bb86fc; padding-left: 15px;">${formatMessage(answerText)}</div>`;

            addMessage(answerText, false);

            if (followUps.length > 0) {
                renderSuggestions(followUps);
            }

        } catch (error) {
            addMessage(`Sorry, trouble connecting: ${error.message}`, false);
            console.error(error);
        } finally {
            toggleLoading(false);
        }
    }

    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
    if (userInput) {
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    // Suggestions Logic
    function renderSuggestions(questions) {
        if (!suggestionChipsContainer) return;
        suggestionChipsContainer.innerHTML = '';
        questions.forEach(q => {
            const btn = document.createElement('button');
            btn.classList.add('suggestion-chip');
            btn.textContent = q;
            btn.addEventListener('click', () => {
                if (userInput) userInput.value = q;
                sendMessage();
            });
            suggestionChipsContainer.appendChild(btn);
        });
    }

    // Bind initial suggestions
    const initialSuggestions = document.querySelectorAll('.suggestion-chip');
    initialSuggestions.forEach(chip => {
        chip.addEventListener('click', () => {
            if (userInput) userInput.value = chip.textContent;
            sendMessage();
        });
    })
});
