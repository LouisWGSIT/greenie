// State
let apiUrl = '';
let currentToken = null;
let currentUsername = null;

// DOM Elements
const floatingBtn = document.getElementById('floatingBtn');
const chatContainer = document.getElementById('chatContainer');
const minimizeBtn = document.getElementById('minimizeBtn');
const closeBtn = document.getElementById('closeBtn');
const updateBtn = document.getElementById('updateBtn');
const settingsBtn = document.getElementById('settingsBtn');
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
    console.log('[Greenie] Initialized with API URL:', apiUrl);
    
    // Test backend connectivity on startup
    try {
        const healthResponse = await fetch(`${apiUrl}/health`, { timeout: 3000 });
        if (healthResponse.ok) {
            const health = await healthResponse.json();
            console.log('[Greenie] Backend is reachable');
            console.log('[Greenie] Security status:', health.security);
            
            // Check if network-only mode is enabled and we're not on private network
            if (health.security?.network_only_mode && !health.security?.is_private_network) {
                console.warn('[Greenie] WARNING: Server is in network-only mode and you are NOT on the private network');
            }
        } else {
            console.warn('[Greenie] Backend returned:', healthResponse.status);
        }
    } catch (e) {
        console.error('[Greenie] Cannot reach backend on startup:', e.message);
    }
    
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
    await window.electronAPI.closeApp();
});

updateBtn.addEventListener('click', async () => {
    console.log('[Greenie] Checking for updates...');
    updateBtn.textContent = '⏳';
    try {
        const result = await window.electronAPI.checkForUpdates();
        console.log('[Greenie] Update check result:', result);
        updateBtn.textContent = result.updateAvailable ? '⬇' : '✓';
        setTimeout(() => {
            updateBtn.textContent = '⬇';
        }, 2000);
    } catch (e) {
        console.error('[Greenie] Update check failed:', e);
        updateBtn.textContent = '⬇';
    }
});

settingsBtn.addEventListener('click', () => {
    console.log('[Greenie] Status check');
    // Show app status in a simple alert or info message
    const status = `Greenie Status:
- User: ${currentUsername || 'Guest'}
- Connected: Yes
- Version: 1.0.0
- API: ${apiUrl}`;
    
    // Add as info message to chat
    addMessage('Greenie', `📊 ${status.replace(/\n/g, ' | ')}`, 'assistant');
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
            body: JSON.stringify({ username, password }),
            timeout: 10000
        });
        
        if (!response.ok) {
            try {
                const error = await response.json();
                loginError.textContent = error.detail || `Login failed (${response.status})`;
            } catch {
                loginError.textContent = `Server error: ${response.status} ${response.statusText}`;
            }
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
        loginError.textContent = `Network error: ${error.message}`;
        loginError.classList.add('visible');
        
        // Log to backend for debugging
        logErrorToBackend({
            message: `Login network error: ${error.message}`,
            type: 'login_network_error',
            details: {
                errorMessage: error.message,
                timestamp: new Date().toISOString(),
                apiUrl: apiUrl
            }
        });
    }
});

// Register
registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = e.target.username.value;
    const email = e.target.email.value;
    const password = e.target.password.value;
    
    console.log('[Greenie Register] Attempting to register with:', { username, email, apiUrl });
    
    try {
        // First, verify backend is reachable
        console.log('[Greenie Register] Testing backend connectivity...');
        let healthOk = false;
        try {
            const healthCheck = await fetch(`${apiUrl}/health`, { timeout: 5000 });
            healthOk = healthCheck.ok;
            console.log('[Greenie Register] Health check:', healthOk ? 'OK' : `Failed (${healthCheck.status})`);
        } catch (hErr) {
            console.error('[Greenie Register] Health check error:', hErr.message);
        }
        
        if (!healthOk) {
            registerError.textContent = `Cannot reach server at ${apiUrl}`;
            registerError.classList.add('visible');
            logErrorToBackend({
                message: `Backend unreachable at startup of registration`,
                type: 'backend_unreachable',
                details: {
                    apiUrl: apiUrl,
                    timestamp: new Date().toISOString()
                }
            });
            return;
        }
        
        console.log('[Greenie Register] Sending registration request...');
        const response = await fetch(`${apiUrl}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password }),
            timeout: 10000
        });
        
        console.log('[Greenie Register] Response status:', response.status);
        
        if (!response.ok) {
            try {
                const error = await response.json();
                registerError.textContent = error.detail || `Registration failed (${response.status})`;
            } catch {
                registerError.textContent = `Server error: ${response.status} ${response.statusText}`;
            }
            registerError.classList.add('visible');
            
            // Log to backend for debugging
            logErrorToBackend({
                message: `Registration failed: HTTP ${response.status}`,
                type: 'registration_error',
                details: {
                    statusCode: response.status,
                    email: email,
                    timestamp: new Date().toISOString()
                }
            });
            return;
        }
        
        registerError.classList.remove('visible');
        console.log('[Greenie Register] Registration successful, auto-logging in...');
        
        // Auto-login after registration
        const loginResponse = await fetch(`${apiUrl}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
            timeout: 10000
        });
        
        if (loginResponse.ok) {
            const data = await loginResponse.json();
            currentToken = data.access_token;
            currentUsername = username;
            
            localStorage.setItem('greenie_auth', JSON.stringify({
                token: currentToken,
                username: currentUsername
            }));
            
            console.log('[Greenie Register] Login successful, showing chat panel');
            showChatPanel();
        } else {
            registerError.textContent = `Auto-login failed: ${loginResponse.status}`;
            registerError.classList.add('visible');
        }
    } catch (error) {
        console.error('[Greenie Register] Caught error:', error);
        registerError.textContent = `Network error: ${error.message}`;
        registerError.classList.add('visible');
        
        // Log to backend for debugging
        logErrorToBackend({
            message: `Registration network error: ${error.message}`,
            type: 'registration_network_error',
            details: {
                errorMessage: error.message,
                timestamp: new Date().toISOString(),
                apiUrl: apiUrl
            }
        });
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
    if (!text || typeof text !== 'string') {
        return String(text || '');
    }
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
            body: JSON.stringify({ message: text }),
            timeout: 30000  // 30 second timeout for Groq API (can be slow)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Chat request failed');
        }
        
        const data = await response.json();
        
        console.log('[Greenie Chat] Response received:', data);
        
        // Remove thinking message
        const thinkingMsg = messages.querySelector('.thinking');
        if (thinkingMsg) {
            thinkingMsg.remove();
        }
        
        // Handle error responses from backend
        if (data.error) {
            console.error('[Greenie Chat] Backend error:', data.error);
            addMessage('Greenie', `❌ Error: ${data.error}`, 'error');
            
            // Log to admin dashboard
            logErrorToBackend({
                message: `Chat error: ${data.error}`,
                type: 'chat_error',
                details: {
                    timestamp: new Date().toISOString(),
                    userMessage: text
                }
            });
            return;
        }
        
        // Handle successful responses
        const reply = data.reply || data.response || data.message || 'No response received';
        console.log('[Greenie Chat] Displaying reply:', reply.substring(0, 100));
        addMessage('Greenie', reply, 'assistant');
    } catch (error) {
        const thinkingMsg = messages.querySelector('.thinking');
        if (thinkingMsg) {
            thinkingMsg.remove();
        }
        
        // Log error to backend
        const errorType = error.message.includes('Cannot reach') ? 'network_error' : 'chat_error';
        logErrorToBackend({
            message: error.message || 'Unknown error',
            type: errorType,
            details: {
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent
            }
        });
        
        const errorMsg = error.message || 'Unknown error occurred';
        addMessage('Greenie', `❌ Error: ${errorMsg}`, 'error');
    }
}

// Log errors to backend for monitoring
async function logErrorToBackend(errorData) {
    try {
        await fetch(`${apiUrl}/api/log-error`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(currentToken && { 'Authorization': `Bearer ${currentToken}` })
            },
            body: JSON.stringify(errorData)
        });
    } catch (e) {
        console.log('Could not send error log to backend');
    }
}

sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});
