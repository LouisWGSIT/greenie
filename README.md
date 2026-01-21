# Greenie - Multi-User AI Assistant

Greenie is a lightweight, multi-user AI assistant built on **Groq API** and **FastAPI**, designed to be deployed on cloud platforms like Render.

## Ì∫Ä Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment
Create a `.env` file:
```
GROQ_API_KEY=your_groq_key_here
JWT_SECRET_KEY=your_secret_key_here
DATABASE_URL=sqlite:///greenie.db
```

Get your free Groq API key: https://console.groq.com

### 3. Start the Server
```bash
python app.py
```

Server runs at: **http://localhost:8000**

## Ì≤¨ Access Chat

### Web UI (Popup)
Open in browser: http://localhost:8000/chat-ui

Features:
- Green floating chat button (Ì≤¨)
- Click to open modal popup
- Sign in / Create account
- Chat with per-user memory
- Lightweight overlay design

## Ì¥ê Authentication

### Register
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"secret123"}'
```

### Login & Get Token
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret123"}'
```

### Authenticated Chat
```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello Greenie!"}'
```

### Anonymous Chat (Default User)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello Greenie!"}'
```

## Ì≥Å Project Structure

```
app.py              - FastAPI server
auth.py             - Authentication & JWT
database.py         - SQLAlchemy models
tools.py            - Utilities
requirements.txt    - Dependencies
static/
  chat.html         - Popup UI
greenie.db          - SQLite database
```

## Ì¥Ñ How It Works

1. **Registration/Login**: Passwords hashed with Argon2, JWT tokens issued
2. **Chat**: Per-user memory & knowledge stored in database, Groq API generates responses
3. **Database**: SQLite (dev), PostgreSQL-ready (production)

## Ì∫¢ Deploy to Render

1. Connect GitHub repo
2. Set environment variables:
   - GROQ_API_KEY
   - JWT_SECRET_KEY
   - DATABASE_URL (PostgreSQL)
3. Render auto-detects app.py and deploys

## ‚ú® Features

- ‚úÖ Free LLM (Groq - 30 req/min)
- ‚úÖ Multi-user with per-user memory
- ‚úÖ JWT authentication
- ‚úÖ SQLite/PostgreSQL support
- ‚úÖ Lightweight popup UI
- ‚úÖ CORS enabled
- ‚úÖ Production-ready FastAPI

## Ì∑™ Testing

```bash
python test_auth.py
```

## Ì≥ù Configuration

See `.env.example` for all options.

## Ì∞õ Troubleshooting

**Port 8000 in use?**
```bash
Get-Process python | Stop-Process -Force
```

**Database reset?**
```bash
rm greenie.db
python app.py
```

---

Built with **Groq API**, **FastAPI**, and **SQLAlchemy**
