# Greenie Deployment Architecture

## Current State (Broken for Users)
```
User's Computer
├── .bat file
├── npm (Node)
├── Electron app ←─┐
└── FastAPI backend ← Electron talks to localhost:8000
```

❌ Problems:
- Closing CMD kills the app
- Users need Python installed
- Users need to run backend manually
- No error logs sent to you
- No way to push updates
- Doesn't scale beyond 1 user

---

## Target State (What You Described - Correct!)
```
User's Computer          |  Your Cloud (Render)
                         |
Electron App ────────────┼──→ FastAPI Backend
  (Greenie.exe)          |    (hosted on Render)
  ├── Chat UI            |    ├── Chat logic
  ├── Auto-update        |    ├── User DB
  ├── Error logging ←────┼────┤ Error logs
  └── No dependencies    |    └── Groq API
                         |
Admin Dashboard ─────────┼──→ Error Logs
  (Your browser)         |    (all user errors)
  ├── View user logs     |
  ├── Manage users       |
  └── Push updates       |
```

✅ Benefits:
- Users: Double-click → works forever
- Backend: Single cloud instance for all users
- Errors: Logged to database, visible in admin panel
- Updates: Auto-download & apply, or user clicks "Update"
- Scaling: One backend serves 10, 100, 1000 users
- Cost: ~$20/month for production

---

## Implementation Steps (Priority Order)

### Phase 1: Fix Current Issues (Today)
- [x] Fix escapeHtml crash
- [x] Fix bat file closing app
- [x] Remove weird command symbols
- [ ] Deploy backend to Render (currently on localhost)
- [ ] Point Electron to Render backend URL

### Phase 2: Add Error Logging (This Week)
- [ ] Create `Error Log` table in PostgreSQL
- [ ] Add logging middleware to FastAPI
- [ ] Save all chat errors, API failures, timeouts
- [ ] Create admin endpoint to view logs

### Phase 3: Create Admin Dashboard (This Week)
- [ ] Add `/admin/logs` endpoint (show all errors)
- [ ] Add `/admin/users` dashboard (view active users)
- [ ] Add `/admin/push-version` endpoint (trigger updates)
- [ ] Simple HTML dashboard at `/admin`

### Phase 4: Auto-Updates (Next Week)
- [ ] Configure electron-builder with GitHub releases
- [ ] Add auto-updater to Electron main.js
- [ ] Users see "Update Available" button in Greenie
- [ ] One-click update without closing the app

### Phase 5: Production Hardening (Next Week)
- [ ] Rate limiting (prevent spam)
- [ ] Better error messages for users
- [ ] Offline mode (cache recent messages locally)
- [ ] Analytics (track which users have errors)

---

## Key URLs After Setup

**Users See:**
- `https://greenie-t89u.onrender.com/` (web version, optional)
- `Greenie.exe` (desktop app, what they use)

**You See (Admin):**
- `https://greenie-t89u.onrender.com/admin` (dashboard)
  - View all user errors
  - See who's using it
  - Push updates

**App Backend:**
- `https://greenie-t89u.onrender.com/chat` (where app sends messages)
- `https://greenie-t89u.onrender.com/auth` (where app authenticates)
- `https://greenie-t89u.onrender.com/health` (health check)

---

## What Needs to Happen Right Now

1. **Verify Render backend is live:**
   ```bash
   curl https://greenie-t89u.onrender.com/health
   # Should return: {"status": "ok"}
   ```

2. **Update Electron app to use Render URL** (not localhost):
   ```javascript
   // In electron/main.js, change from:
   const API_URL = 'http://localhost:8000';
   // To:
   const API_URL = 'https://greenie-t89u.onrender.com';
   ```

3. **Test with cloud backend:**
   - Stop local FastAPI
   - Start Electron
   - Try to sign in and chat
   - Should work with Render backend

4. **Build installer for distribution:**
   ```bash
   cd electron
   npm run build:win
   # Creates: electron/dist/Greenie Setup 1.0.0.exe
   ```

---

## For End Users (Super Simple)

1. **First Time:**
   - Download `Greenie.exe`
   - Double-click
   - Green icon appears in system tray
   - Click "Sign In" and create account
   - Start chatting

2. **Every Time After:**
   - Double-click `Greenie.exe`
   - Chat opens
   - Done

3. **When You Push Updates:**
   - Their app shows "Update Available"
   - They click "Update"
   - App restarts with new version
   - No manual intervention needed

---

## Error Logging Flow

```
User encounters error in Greenie
  ↓
Electron app catches error
  ↓
Sends to backend: POST /api/error-log
  {
    "user_id": 123,
    "message": "Chat response failed",
    "error_type": "network_timeout",
    "timestamp": "2026-01-21T10:30:00Z"
  }
  ↓
Backend stores in PostgreSQL error_logs table
  ↓
You check admin dashboard: /admin/logs
  ↓
You see: "5 users had timeouts in last hour"
  ↓
You fix the issue and push update
  ↓
All users get "Update Available" notification
```

---

## Cost Breakdown (Monthly)

- **Render Web Service:** $0-7 (free tier or Starter)
- **Render PostgreSQL:** $15 (2GB, backups)
- **Groq API:** $0 (30 req/min free tier is usually enough)
- **GitHub:** $0 (free)
- **Domain (optional):** $0-12/year

**Total:** $15/month for production-grade setup

---

## Questions?

This architecture is standard for SaaS products:
- Slack, Discord, Figma, etc. all work this way
- User downloads app once, backend is cloud-hosted
- You maintain one backend, serve unlimited users
- One-click deployment and updates

Ready to implement this?
