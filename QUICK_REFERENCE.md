# Greenie Quick Reference

## Start Server
```bash
python app.py
```

## Access UI
```
http://localhost:8000/chat-ui
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Register User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@test.com","password":"secret"}'
```

### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret"}'
```
Returns: `{"access_token":"...", "token_type":"bearer"}`

### Chat (Authenticated)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello!"}'
```

### Chat (Anonymous)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello!"}'
```

### Get Current User
```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer TOKEN_HERE"
```

## Environment Variables
```
GROQ_API_KEY=gsk_...          # Free API key from console.groq.com
JWT_SECRET_KEY=your_secret    # Change in production
DATABASE_URL=sqlite:///greenie.db  # SQLite (dev) or PostgreSQL (prod)
```

## Files
- `app.py` - Main FastAPI server
- `auth.py` - User authentication
- `database.py` - Database models
- `static/chat.html` - Popup UI
- `greenie.db` - SQLite database
- `requirements.txt` - Dependencies

## Troubleshooting
```bash
# Kill Python process
Get-Process python | Stop-Process -Force

# Reset database
rm greenie.db
python app.py

# Check logs
cat greenie.log
```

## Deploy to Render
1. Push to GitHub
2. Connect GitHub to Render
3. Set environment variables (GROQ_API_KEY, JWT_SECRET_KEY, DATABASE_URL)
4. Deploy (auto-detects app.py)

---

See [README.md](README.md) for full docs | See [STARTUP_GUIDE.md](STARTUP_GUIDE.md) for setup
