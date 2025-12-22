document.addEventListener('DOMContentLoaded', () => {
    const chatHistory = document.getElementById('chat-history');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const dailyStoryBtn = document.getElementById('daily-story-btn');
    const suggestionChipsContainer = document.querySelector('.suggestions-container');
    const loadingOverlay = document.getElementById('loading-overlay');
    const authContainer = document.getElementById('auth-container');

    // Check Auth Status
    async function checkAuth() {
        if (!authContainer) return;
        try {
            const res = await fetch('/auth/me');
            const data = await res.json();
            if (data.authenticated) {
                // Show User Profile
                authContainer.innerHTML = `
                    <div class="user-profile">
                        <img src="${data.user.picture}" alt="${data.user.display_name}" class="user-avatar" title="${data.user.display_name}">
                        <a href="/auth/logout" class="auth-btn logout-btn">Logout</a>
                    </div>
                `;
            } else {
                // Show Login Button
                authContainer.innerHTML = `
                    <a href="/auth/login" class="auth-btn">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                             <path d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"/>
                        </svg>
                        Login with Google
                    </a>
                `;
            }
        } catch (e) {
            console.error("Auth check failed", e);
        }
    }
    checkAuth();

    // Shloka Elements
    const shlokaBtn = document.getElementById('shloka-btn');
    const shlokaModal = document.getElementById('shloka-modal');
    const closeModal = document.querySelector('.close-modal');
    const shlokaSanskrit = document.getElementById('shloka-sanskrit');
    const shlokaTransliteration = document.getElementById('shloka-transliteration');
    const shlokaMeaning = document.getElementById('shloka-meaning');
    const shlokaSource = document.getElementById('shloka-source');

    let shlokasData = [];

    // Load Shlokas
    async function loadShlokas() {
        try {
            const response = await fetch('shlokas.json');
            if (response.ok) {
                shlokasData = await response.json();
            }
        } catch (error) {
            console.error("Failed to load shlokas:", error);
        }
    }
    loadShlokas();

    if (shlokaBtn) {
        shlokaBtn.addEventListener('click', () => {
            if (shlokasData.length === 0) return;
            const randomShloka = shlokasData[Math.floor(Math.random() * shlokasData.length)];

            // Format Shloka for Chat
            const shlokaHTML = `
                <div style="text-align: center; margin-bottom: 5px; white-space: normal;">
                    <strong style="color: #feca57; font-size: 1.1rem; display: block; margin-bottom: 4px;">${randomShloka.sanskrit}</strong>
                    <em style="color: rgba(255,255,255,0.8); display: block; margin-bottom: 8px; font-size: 0.95rem;">${randomShloka.transliteration}</em>
                    <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 6px 0;">
                    <span style="display: block; margin-bottom: 4px;">${randomShloka.meaning}</span>
                    <small style="color: #ff9f43; text-transform: uppercase; font-size: 0.75rem;">— ${randomShloka.source}</small>
                </div>
            `;

            // Add as bot message
            addMessage(shlokaHTML, false);
        });
    }

    // Modal logic removed as requested


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
            // Check if it looks like our internal HTML format (starts with <div for shlokas)
            // or perform standard markdown formatting
            if (typeof text === 'string' && text.trim().startsWith('<div')) {
                msgDiv.innerHTML = text; // Trusted internal content from shloka button
            } else {
                msgDiv.innerHTML = formatMessage(text);
            }
        }

        chatHistory.appendChild(msgDiv);

        // Ensure smooth scroll to the new message
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
            const response = await fetch('/api/ask?question=' + encodeURIComponent(text), {
                method: 'POST'
            });
            if (!response.ok) {
                const errText = await response.text();
                try {
                    const errJson = JSON.parse(errText);
                    throw new Error(errJson.answer || `Server Error: ${response.status}`);
                } catch (e) {
                    throw new Error(`Server Error: ${response.status} - ${errText}`);
                }
            }
            const data = await response.json();

            let answerText = "";
            let followUps = [];

            if (typeof data.answer === 'object' && data.answer !== null) {
                answerText = data.answer.answer || JSON.stringify(data.answer);
            } else if (typeof data.answer === 'string') {
                try {
                    const inner = JSON.parse(data.answer);
                    if (inner.answer) {
                        answerText = inner.answer;
                        followUps = inner.follow_up_questions || [];
                    } else {
                        answerText = data.answer;
                    }
                } catch {
                    answerText = data.answer;
                }
            }

            if (data.answer && data.answer.answer) {
                answerText = data.answer.answer;
                followUps = data.answer.follow_up_questions || [];
            } else if (data.answer) {
                answerText = data.answer;
            }

            addMessage(answerText, false);

            if (followUps.length > 0) {
                renderSuggestions(followUps);
            } else {
                renderSuggestions(getRandomQuestions());
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

    // Pool of 20+ Wisdom Questions
    const wisdomQuestions = [
        "What is the true nature of the Self (Atman)?",
        "How can I overcome anxiety according to the Gita?",
        "What is the meaning of Dharma in daily life?",
        "Explain the concept of Karma Yoga.",
        "What happens to the soul after death?",
        "How does meditation (Dhyana) lead to peace?",
        "What is the significance of 'Om'?",
        "How can one control the restless mind?",
        "What is the difference between ego and self?",
        "Why do bad things happen to good people?",
        "What is Maya (Illusion)?",
        "How to detach from results of action?",
        "What is the path of Bhakti (Devotion)?",
        "Who is a Sthita-prajna (Stable Wisdom)?",
        "What is the role of a Guru?",
        "How to deal with anger and attachment?",
        "What is the ultimate goal of human life?",
        "Is destiny pre-determined?",
        "What is the relationship between Brahman and Atman?",
        "How to find purpose in life?"
    ];

    function getRandomQuestions() {
        const shuffled = [...wisdomQuestions].sort(() => 0.5 - Math.random());
        return shuffled.slice(0, 4);
    }

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

    // Initial Render
    renderSuggestions(getRandomQuestions());

    if (dailyStoryBtn) {
        // dailyStoryBtn.addEventListener('click', async () => {
        //     dailyStoryBtn.disabled = true;
        //     dailyStoryBtn.textContent = "Generating...";
        //     try {
        //         await fetch('/api/trigger-daily-story', { method: 'POST' });
        //         alert("Daily story generation triggered! Check the logs/output.");
        //     } catch (error) {
        //         console.error(error);
        //         alert("Failed to trigger story.");
        //     } finally {
        //         dailyStoryBtn.disabled = false;
        //         dailyStoryBtn.textContent = "Generate Daily Wisdom";
        //     }
        // });
    }
});
