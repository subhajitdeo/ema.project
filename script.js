// script.js - Zara.ai Core: Speech, AI Tool System, OpenRouter, LocalStorage Memory

// ---------- DOM Elements ----------
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
const apiKeyInput = document.getElementById('apiKeyInput');
const saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
const thinkingIndicator = document.getElementById('thinkingIndicator');
const voiceStatusSpan = document.getElementById('voiceStatus');
const aiOrb = document.getElementById('aiOrb');
const soundWave = document.getElementById('soundWave');

// ---------- App State ----------
let openRouterApiKey = localStorage.getItem('zara_openrouter_key') || '';
let isListening = false;
let recognition = null;
let synth = window.speechSynthesis;

// Load API key to input field
if (openRouterApiKey) apiKeyInput.value = openRouterApiKey;

// Save API key
saveApiKeyBtn.addEventListener('click', () => {
    openRouterApiKey = apiKeyInput.value.trim();
    if (openRouterApiKey) {
        localStorage.setItem('zara_openrouter_key', openRouterApiKey);
        addSystemMessage('🔑 API key saved. You can now use Zara AI.', false);
    } else {
        localStorage.removeItem('zara_openrouter_key');
        addSystemMessage('⚠️ API key removed, some features limited.', false);
    }
});

// Helper: add message to chat history
function addMessage(text, isUser, toolData = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
    const avatarIcon = isUser ? '<i class="fas fa-user-astronaut"></i>' : '<i class="fas fa-microchip"></i>';
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute:'2-digit' });
    
    let sourceHtml = '';
    if (toolData && toolData.sourceLinks && toolData.sourceLinks.length) {
        sourceHtml = `<div class="source-links">${toolData.sourceLinks.map(link => `<a href="${link.url}" target="_blank" class="source-link"><i class="fas fa-external-link-alt"></i> ${link.label}</a>`).join('')}</div>`;
    }
    
    messageDiv.innerHTML = `
        <div class="avatar">${avatarIcon}</div>
        <div class="content">
            <p>${text}</p>
            ${sourceHtml}
        </div>
        <div class="timestamp">${timestamp}</div>
    `;
    chatMessages.appendChild(messageDiv);
    messageDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    // Save to localStorage memory (simple history)
    let history = JSON.parse(localStorage.getItem('zara_chat_history') || '[]');
    history.push({ role: isUser ? 'user' : 'assistant', content: text, timestamp: Date.now() });
    if (history.length > 50) history = history.slice(-50);
    localStorage.setItem('zara_chat_history', JSON.stringify(history));
}

function addSystemMessage(text, isError = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ai-message`;
    msgDiv.style.opacity = '0.8';
    msgDiv.innerHTML = `<div class="avatar"><i class="fas fa-info-circle"></i></div><div class="content"><p style="color:${isError?'#ff9999':'#aaffdd'}">⚡ ${text}</p></div>`;
    chatMessages.appendChild(msgDiv);
    msgDiv.scrollIntoView({ behavior: 'smooth' });
}

// Text-to-Speech
function speakText(text) {
    if (!synth) return;
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1.1;
    utterance.voice = synth.getVoices().find(v => v.lang.includes('en-US')) || null;
    synth.speak(utterance);
}

// ---------- TOOL SYSTEM + AI RESPONSE HANDLER ----------
// Built-in tools: Weather (free API fallback), News (simulated summarization + open websites), YouTube, Wikipedia, Google
// The AI will return JSON with tool, speak, open, and extra context.

async function executeToolCommand(toolObj) {
    // toolObj: { tool, speak, open, query, summary?, additionalData? }
    const { tool, speak, open: urlToOpen, query, summary, newsItems } = toolObj;
    
    // Speak first
    if (speak) {
        speakText(speak);
        addMessage(speak, false, { sourceLinks: urlToOpen ? [{ label: `Open ${tool.toUpperCase()} Source`, url: urlToOpen }] : [] });
    } else {
        addMessage("Action completed.", false);
    }
    
    // Open website in new tab
    if (urlToOpen) {
        setTimeout(() => {
            window.open(urlToOpen, '_blank');
        }, 800);
    }
    
    // For weather: we can fetch real data using Open-Meteo (free, no key) to enrich answer if AI didn't provide full details
    if (tool === 'weather' && query) {
        try {
            // query example: "London" or "current weather"
            const location = query.replace(/weather|in|for/gi, '').trim();
            if (location) {
                const geoUrl = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(location)}&count=1&language=en&format=json`;
                const geoRes = await fetch(geoUrl);
                const geoData = await geoRes.json();
                if (geoData.results && geoData.results.length) {
                    const { latitude, longitude, name } = geoData.results[0];
                    const weatherUrl = `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current_weather=true&timezone=auto`;
                    const wRes = await fetch(weatherUrl);
                    const wData = await wRes.json();
                    if (wData.current_weather) {
                        const temp = wData.current_weather.temperature;
                        const wind = wData.current_weather.windspeed;
                        const weatherText = `🌡️ Real-time: ${temp}°C, Wind ${wind} km/h in ${name}.`;
                        addMessage(weatherText, false);
                        speakText(weatherText);
                    }
                }
            }
        } catch(e) { console.warn("weather fetch fallback"); }
    }
    
    // For news: provide top story suggestions, open BBC/Reuters automatically
    if (tool === 'news') {
        // automatically open Reuters or BBC
        setTimeout(() => {
            window.open('https://www.reuters.com/', '_blank');
            addMessage("📰 Opened Reuters for trusted news.", false);
        }, 1200);
    }
}

// Main AI function: call OpenRouter + parse tool JSON
async function askZara(userPrompt) {
    if (!openRouterApiKey) {
        addSystemMessage("⚠️ Please enter your OpenRouter API key (top right). Get one at openrouter.ai/keys", true);
        speakText("Please set your OpenRouter API key first.");
        return;
    }
    
    thinkingIndicator.classList.add('active');
    try {
        // Build conversation memory from localStorage (last 6 exchanges)
        let history = JSON.parse(localStorage.getItem('zara_chat_history') || '[]');
        let recent = history.slice(-8);
        let messages = [
            { role: "system", content: `You are Zara, a futuristic AI assistant. You must answer naturally and use tools when appropriate. 
            Format your response as a JSON object with fields: tool, speak, open (optional URL), query (search term), and optionally summary.
            Available tools: "weather" (user asks weather), "news" (latest news), "youtube" (search youtube), "wikipedia" (search wiki), "google" (general search), "none".
            For weather: open URL "https://windy.com" or "https://weather.com". For news: open "https://reuters.com", speak summary. For youtube: open "https://youtube.com/results?search_query=QUERY". 
            For wikipedia: open "https://en.wikipedia.org/wiki/QUERY".
            Example: {"tool":"youtube","speak":"Opening YouTube search for cats","open":"https://youtube.com/results?search_query=cats","query":"cats"}
            Example weather: {"tool":"weather","speak":"Let me show you live weather radar","open":"https://windy.com","query":"New York"}
            Example news: {"tool":"news","speak":"Here are the latest headlines. Opening Reuters.","open":"https://reuters.com","summary":"Global tensions rise..."}
            Respond ONLY with valid JSON. Do not add extra text.` },
            ...recent.map(m => ({ role: m.role, content: m.content })),
            { role: "user", content: userPrompt }
        ];
        
        const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${openRouterApiKey}`,
                "Content-Type": "application/json",
                "HTTP-Referer": window.location.origin,
                "X-Title": "Zara AI Assistant"
            },
            body: JSON.stringify({
                model: "openai/gpt-3.5-turbo", // or "mistralai/mistral-7b-instruct"
                messages: messages,
                temperature: 0.4,
                max_tokens: 300
            })
        });
        
        if (!response.ok) {
            const errData = await response.text();
            throw new Error(`API Error: ${response.status} ${errData}`);
        }
        
        const data = await response.json();
        let aiRaw = data.choices[0].message.content;
        // Clean possible markdown json
        aiRaw = aiRaw.replace(/```json/g, '').replace(/```/g, '').trim();
        let aiJson;
        try {
            aiJson = JSON.parse(aiRaw);
        } catch(e) {
            // fallback: treat as normal reply without tool
            aiJson = { tool: "none", speak: aiRaw.substring(0, 200), open: null };
        }
        
        // Validate tool
        const validTools = ['weather', 'news', 'youtube', 'wikipedia', 'google', 'none'];
        if (!validTools.includes(aiJson.tool)) aiJson.tool = 'none';
        
        // Process tool actions
        if (aiJson.tool !== 'none') {
            if (aiJson.tool === 'youtube' && aiJson.query) {
                aiJson.open = `https://www.youtube.com/results?search_query=${encodeURIComponent(aiJson.query)}`;
            }
            if (aiJson.tool === 'wikipedia' && aiJson.query) {
                aiJson.open = `https://en.wikipedia.org/wiki/${encodeURIComponent(aiJson.query.replace(/ /g, '_'))}`;
            }
            if (aiJson.tool === 'google' && aiJson.query) {
                aiJson.open = `https://www.google.com/search?q=${encodeURIComponent(aiJson.query)}`;
            }
            if (aiJson.tool === 'weather' && !aiJson.open) aiJson.open = "https://windy.com";
            if (aiJson.tool === 'news' && !aiJson.open) aiJson.open = "https://reuters.com";
            
            await executeToolCommand(aiJson);
        } else {
            // Standard conversational answer
            let replyText = aiJson.speak || (typeof aiJson === 'object' ? "Processing..." : aiRaw);
            if (replyText.length < 5) replyText = aiRaw.substring(0, 300);
            addMessage(replyText, false);
            speakText(replyText);
        }
        
    } catch (error) {
        console.error(error);
        addSystemMessage(`❌ AI error: ${error.message}. Check API key or network.`, true);
        speakText("Sorry, I encountered an error. Check your API key.");
    } finally {
        thinkingIndicator.classList.remove('active');
    }
}

// ---------- Voice Recognition ----------
function initSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        addSystemMessage("❌ Voice recognition not supported in this browser. Use typing.", true);
        micBtn.disabled = true;
        return null;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recog = new SpeechRecognition();
    recog.continuous = false;
    recog.interimResults = false;
    recog.lang = 'en-US';
    
    recog.onstart = () => {
        isListening = true;
        micBtn.classList.add('listening');
        soundWave.classList.add('active');
        voiceStatusSpan.innerText = "🎤 Listening... speak now";
        aiOrb.style.boxShadow = "0 0 30px #ff3399";
    };
    recog.onend = () => {
        isListening = false;
        micBtn.classList.remove('listening');
        soundWave.classList.remove('active');
        voiceStatusSpan.innerText = "";
        aiOrb.style.boxShadow = "0 0 20px cyan";
    };
    recog.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        userInput.value = transcript;
        voiceStatusSpan.innerText = `🗣️ Recognized: "${transcript}"`;
        setTimeout(() => voiceStatusSpan.innerText = "", 2000);
        // Automatically send
        processUserInput(transcript);
    };
    recog.onerror = (e) => {
        voiceStatusSpan.innerText = `🎙️ Error: ${e.error}`;
        setTimeout(() => voiceStatusSpan.innerText = "", 1500);
        micBtn.classList.remove('listening');
        soundWave.classList.remove('active');
    };
    return recog;
}

function startListening() {
    if (!recognition) {
        recognition = initSpeechRecognition();
        if (!recognition) return;
    }
    if (isListening) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

// handle typed or voice input
async function processUserInput(text) {
    if (!text.trim()) return;
    addMessage(text, true);
    userInput.value = "";
    await askZara(text);
}

// Event listeners
sendBtn.addEventListener('click', () => processUserInput(userInput.value));
userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') processUserInput(userInput.value); });
micBtn.addEventListener('click', startListening);

// Additional: Load previous chat history from localStorage on startup
function loadChatHistory() {
    let history = JSON.parse(localStorage.getItem('zara_chat_history') || '[]');
    if (history.length === 0) return;
    // show last 12 messages
    const lastMessages = history.slice(-12);
    chatMessages.innerHTML = '';
    lastMessages.forEach(msg => {
        const isUser = msg.role === 'user';
        addMessage(msg.content, isUser);
    });
    if (lastMessages.length) addSystemMessage("🔄 Loaded previous conversation from memory", false);
}
loadChatHistory();

// small intro effect
setTimeout(() => {
    speakText("Zara AI ready. Use your voice or type.");
}, 800);
