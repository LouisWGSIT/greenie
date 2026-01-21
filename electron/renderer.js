// State
let apiUrl = '';
let currentToken = null;
let currentUsername = null;

// DOM Elements
const floatingBtn = document.getElementById('floatingBtn');
const chatContainer = document.getElementById('chatContainer');
const minimizeBtn = document.getElementById('minimizeBtn');
const closeBtn = document.getElementById('closeBtn');
const authPanel = document.getElementById('authPanel');
const chatPanel = document.getElementById('chatPanel');
const userInfo = document.getElementById('userInfo');
const inputArea = document.getElementById('inputArea');
const messages = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const currentUserSpan = document.getElementById('currentUser');
const logoutBtn = document.getElementById('logoutBtn');
const guestLink = document.getElementById('guestLink');

// Auth tabs
const authTabs = document.querySelectorAll('.auth-tab');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const loginError = document.getElementById('loginError');
const registerError = document.getElementById('registerError');

// Initialize
(async function init() {
    apiUrl = await window.electronAPI.getApiUrl();
    
    // Check for saved token
    const saved = localStorage.getItem('greenie_auth');
    if (saved) {
        try {
            const data = JSON.parse(saved);
            currentToken = data.token;
            currentUsername = data.username;
            showChatPanel();
        } catch (e) {
            localStorage.removeItem('greenie_auth');
        }
    }
})();

// Show/Hide
floatingBtn.addEventListener('click', () => {
    chatContainer.classList.add('active');
    floatingBtn.classList.add('hidden');
});

minimizeBtn.addEventListener('click', () => {
    chatContainer.classList.remove('active');
    floatingBtn.classList.remove('hidden');
});

closeBtn.addEventListener('click', async () => {
    await window.electronAPI.minimizeWindow();
});

// Auth Tabs
authTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        authTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        document.querySelectorAll('.auth-form').forEach(form => {
            form.classList.remove('active');
        });
        
        if (tabName === 'login') {
            loginForm.classList.add('active');
        } else {
            registerForm.classList.add('active');
        }
    });
});

// Login
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = e.target.username.value;
    const password = e.target.password.value;
    
    try {
        const response = await fetch(`${apiUrl}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            const error = await response.json();
            loginError.textContent = error.detail || 'Login failed';
            loginError.classList.add('visible');
            return;
        }
        
        const data = await response.json();
        currentToken = data.access_token;
        currentUsername = username;
        
        // Save to localStorage
        localStorage.setItem('greenie_auth', JSON.stringify({
            token: currentToken,
            username: currentUsername
        }));
        
        loginError.classList.remove('visible');
        showChatPanel();
    } catch (error) {
        loginError.textContent = 'Network error. Please try again.';
        loginError.classList.add('visible');
    }
});

// Register
registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = e.target.username.value;
    const email = e.target.email.value;
    const password = e.target.password.value;
    
    try {
        const response = await fetch(`${apiUrl}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        
        if (!response.ok) {
            const error = await response.json();
            registerError.textContent = error.detail || 'Registration failed';
            registerError.classList.add('visible');
            return;
        }
        
        registerError.classList.remove('visible');
        
        // Auto-login after registration
        const loginResponse = await fetch(`${apiUrl}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (loginResponse.ok) {
            const data = await loginResponse.json();
            currentToken = data.access_token;
            currentUsername = username;
            
            localStorage.setItem('greenie_auth', JSON.stringify({
                token: currentToken,
                username: currentUsername
            }));
            
            showChatPanel();
        }
    } catch (error) {
        registerError.textContent = 'Network error. Please try again.';
        registerError.classList.add('visible');
    }
});

// Logout
logoutBtn.addEventListener('click', () => {
    currentToken = null;
    currentUsername = null;
    localStorage.removeItem('greenie_auth');
    
    authPanel.classList.remove('hidden');
    chatPanel.classList.remove('active');
    userInfo.classList.remove('active');
    inputArea.classList.remove('active');
    messages.innerHTML = '';
    
    loginForm.reset();
    registerForm.reset();
});

// Guest Mode
guestLink.addEventListener('click', () => {
    showChatPanel(true);
});

// Show Chat Panel
function showChatPanel(isGuest = false) {
    authPanel.classList.add('hidden');
    chatPanel.classList.add('active');
    inputArea.classList.add('active');
    
    if (!isGuest) {
        userInfo.classList.add('active');
        currentUserSpan.textContent = currentUsername;
    }
    
    messages.innerHTML = '';
    addMessage('Greenie', 'Hi there! How can I help you today?', 'assistant');
}

// Add Message with Avatars
function addMessage(sender, text, type = 'user') {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;
    
    let avatarHtml = '';
    if (type === 'assistant') {
        // Greenie avatar - show Greenie.png icon from assets
        // Use relative path since this runs in renderer context
        avatarHtml = `<img src="../assets/Greenie.png" alt="Greenie" class="avatar greenie-avatar" onerror="this.style.display='none'" />`;
    } else if (type === 'user' || type === 'thinking') {
        // User avatar - show first letter of username
        const initial = (currentUsername || 'G')[0].toUpperCase();
        avatarHtml = `<div class="avatar user-avatar">${initial}</div>`;
    }
    
    msgDiv.innerHTML = `
        ${avatarHtml}
        <div class="message-bubble">${escapeHtml(text)}</div>
    `;
    messages.appendChild(msgDiv);
    messages.scrollTop = messages.scrollHeight;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Send Message
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;
    
    messageInput.value = '';
    addMessage('You', text, 'user');
    addMessage('Greenie', 'Thinking...', 'thinking');
    
    try {
        // Check if backend is reachable
        try {
            const healthCheck = await fetch(`${apiUrl}/health`, { timeout: 3000 });
            if (!healthCheck.ok) {
                throw new Error('Backend not responding');
            }
        } catch (e) {
            const thinkingMsg = messages.querySelector('.thinking');
            if (thinkingMsg) thinkingMsg.remove();
            addMessage('Greenie', '❌ Cannot reach the server. Please start the FastAPI backend:\n\nIn a new terminal:\ncd "C:\\Users\\Louisw\\Documents\\AI Agent"\npython app.py', 'error');
            return;
        }

        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (currentToken) {
            headers['Authorization'] = `Bearer ${currentToken}`;
        }
        
        const response = await fetch(`${apiUrl}/chat`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ message: text })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Chat request failed');
        }
        
        const data = await response.json();
        
        // Remove thinking message
        const thinkingMsg = messages.querySelector('.thinking');
        if (thinkingMsg) {
            thinkingMsg.remove();
        }
        
        addMessage('Greenie', data.response, 'assistant');
    } catch (error) {
        const thinkingMsg = messages.querySelector('.thinking');
        if (thinkingMsg) {
            thinkingMsg.remove();
        }
        const errorMsg = error.message || 'Unknown error occurred';
        addMessage('Greenie', `❌ Error: ${errorMsg}`, 'error');
    }
}

sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});
