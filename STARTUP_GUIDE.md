# Greenie Startup Guide

## Prerequisites
- Python 3.10+
- Free Groq API key (get at https://console.groq.com)

## Installation

### 1. Clone/Download Greenie
```bash
cd "path/to/Greenie"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Create `.env` File
In the Greenie folder, create `.env`:
```
GROQ_API_KEY=gsk_your_key_here
JWT_SECRET_KEY=your_secret_key_change_in_production
DATABASE_URL=sqlite:///greenie.db
```

**Get Groq Key:**
1. Go to https://console.groq.com
2. Sign up (free)
3. Create API key in Settings
4. Copy and paste into `.env`

## Starting Greenie

### Option 1: Terminal
```bash
python app.py
```

Server starts at: **http://localhost:8000**

### Option 2: Background (Keep Running)
**Windows (PowerShell):**
```powershell
Start-Process python -ArgumentList "app.py" -WindowStyle Hidden
```

**Mac/Linux:**
```bash
nohup python app.py &
```

## Access Chat UI

### In Browser
```
http://localhost:8000/chat-ui
```

You'll see:
- Green floating chat button (í²¬) in bottom-right
- Click to open popup
- Sign in or chat as guest
- Lightweight popup (not full-page)

## Testing

### Quick Test
```bash
curl http://localhost:8000/health
```

Should return:
```json
{"ok": true, "groq_configured": true, "groq_status": "connected"}
```

### Run Tests
```bash
python test_auth.py
```

## First Time Setup

### 1. Register a User
Click "Create Account" in popup and sign up.

### 2. Start Chatting
- Type a question
- Greenie responds using Groq API
- Your messages saved to database (per-user)

### 3. (Optional) Chat via API
```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"bob","email":"bob@example.com","password":"secret"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"bob","password":"secret"}'

# Chat (with token from login response)
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello!"}'
```

## Troubleshooting

### Port 8000 Already in Use
```bash
# Kill Python process
Get-Process python | Stop-Process -Force
```

### Groq API Not Working
- Check `.env` has GROQ_API_KEY
- Verify key at https://console.groq.com
- Check rate limits: 30 requests/min

### Database Issues
```bash
# Delete database and restart
rm greenie.db
python app.py
```

### Logs
- `greenie.log` - server activity
- Look in terminal output for errors

## Production Deployment

See [README.md](README.md) for Render deployment steps.

## Support

- **Groq API docs**: https://console.groq.com/docs
- **FastAPI docs**: http://localhost:8000/docs (when server running)

---

Ready? Start with: `python app.py`
