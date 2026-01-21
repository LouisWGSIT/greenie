# Greenie Render Deployment Guide

## Overview

This guide walks you through deploying Greenie to **Render** for free (or very cheap).

**What you'll get:**
- ✅ FastAPI backend running 24/7
- ✅ Free PostgreSQL database (500 MB)
- ✅ Groq API (free, 30 req/min)
- ✅ Chat accessible from any device
- ✅ Total cost: $0-$7/month

## Prerequisites

1. **GitHub Account** - To connect your repo
2. **Groq API Key** - Get free at https://console.groq.com
3. **Render Account** - Free signup at https://render.com

## Step 1: Prepare Code for Deployment

### 1.1 Add Render Build Script

Create `render_build.sh` (in project root):

```bash
#!/bin/bash
pip install -r requirements.txt
```

Make it executable:
```bash
chmod +x render_build.sh
```

### 1.2 Update app.py for Render

Your `app.py` already handles this, but verify:

```python
DATABASE_URL = os.environ.get("DATABASE_URL")  # Render sets this
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")  # You'll set this
```

The app auto-converts `postgres://` to `postgresql://` for compatibility.

### 1.3 Verify requirements.txt

Check you have all dependencies (should be pre-done):

```bash
pip freeze > requirements_current.txt
```

Ensure `requirements.txt` has:
- fastapi
- uvicorn
- groq
- sqlalchemy
- psycopg2-binary (PostgreSQL driver)
- passlib
- argon2-cffi
- python-jose
- python-multipart

## Step 2: Push Code to GitHub

### 2.1 Initialize Git (if not already)

```bash
cd path/to/Greenie
git init
git add .
git commit -m "Initial commit: Greenie ready for Render deployment"
```

### 2.2 Create GitHub Repo

1. Go to https://github.com/new
2. Name it `greenie`
3. Click "Create repository"
4. Copy the push commands and run them

### 2.3 Push to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/greenie.git
git branch -M main
git push -u origin main
```

## Step 3: Create Render Web Service

### 3.1 Go to Render

1. Visit https://render.com
2. Sign up (free)
3. Click **"New +"** → **"Web Service"**

### 3.2 Connect GitHub

1. Click **"Connect GitHub account"** if not already
2. Authorize Render
3. Search for your `greenie` repo
4. Click to connect

### 3.3 Configure Web Service

Fill in the form:

| Field | Value |
|-------|-------|
| **Name** | `greenie` |
| **Environment** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app:app --host 0.0.0.0 --port $PORT` |
| **Plan** | `Free` (or Starter if you want reliability) |

### 3.4 Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"**

Add these (one by one):

```
GROQ_API_KEY = gsk_your_key_here
```

```
JWT_SECRET_KEY = your_super_secret_key_here_change_this
```

**DO NOT set DATABASE_URL here yet** (Render will set this automatically when you attach PostgreSQL).

### 3.5 Create Service

Click **"Create Web Service"**

Render will:
1. Clone your repo
2. Install dependencies
3. Start your app
4. Assign you a URL like `https://greenie-xxxxx.onrender.com`

Wait 2-3 minutes for first deploy. You'll see logs in the "Logs" tab.

## Step 4: Add PostgreSQL Database

### 4.1 Create Database

1. Click **"New +"** → **"PostgreSQL"**
2. Name it `greenie-db`
3. Region: same as your web service (e.g., `Ohio`)
4. Plan: `Free` (comes with 500 MB)
5. Click **"Create Database"**

Wait for DB to start (~2 minutes).

### 4.2 Connect Database to Web Service

1. Go back to your `greenie` **Web Service**
2. Click **"Environment"**
3. Click **"Add Environment Variable"** (or scroll down)
4. You should see `DATABASE_URL` pre-populated! ✅

If not, grab the connection string from your PostgreSQL database page and add it:

```
DATABASE_URL = postgresql://user:password@host:5432/greenie
```

### 4.3 Redeploy

Your app will automatically redeploy with the database connection.

## Step 5: Test Deployment

### 5.1 Check Service is Running

1. Go to your Web Service in Render
2. Look for green **"Live"** indicator
3. Click the URL to visit your app

### 5.2 Test Health Endpoint

```bash
curl https://greenie-xxxxx.onrender.com/health
```

Should return:
```json
{"ok": true, "groq_configured": true, "groq_status": "connected"}
```

### 5.3 Test Chat UI

Open in browser:
```
https://greenie-xxxxx.onrender.com/chat-ui
```

You should see:
- Green floating button (💬)
- Click to open popup
- Sign up and chat!

## Step 6: Manage Your Deployment

### View Logs

In Render dashboard → your service → **"Logs"** tab

### Redeploy

Whenever you push changes to GitHub:
```bash
git add .
git commit -m "Update feature"
git push
```

Render auto-redeploys!

### Scale Up (Optional)

If you hit free tier limits:
- 0.5 vCPU, 512 MB RAM
- Spins down after 15 min inactivity (standard free tier)

To always run: Upgrade to **Starter** ($7/month)

## Troubleshooting

### App keeps crashing?
1. Check **Logs** tab in Render
2. Look for errors
3. Common issues:
   - Missing environment variable
   - Database connection string wrong
   - Python version mismatch

### Can't connect to PostgreSQL?
1. Verify `DATABASE_URL` is set in Environment
2. Render auto-adds it when you create DB
3. If missing, manually add from PostgreSQL page

### Rate limited on Groq API?
- Free tier: 30 requests/min, 14,400 tokens/min
- If you exceed: wait for next minute or upgrade Groq account

### Chat not responding?
1. Test with curl:
```bash
curl -X POST https://greenie-xxxxx.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"test"}'
```

2. Check logs in Render dashboard

## Monitoring & Maintenance

### Monitor Usage

In Render dashboard:
- **Metrics** tab shows CPU, RAM, bandwidth
- Free tier gets 750 hours/month (enough for 24/7)

### Database Backups

Render PostgreSQL free tier does NOT include auto-backups.

For production, consider:
- Upgrading to Starter ($15/month with backups)
- Or manually export data

### Logs Retention

Render keeps logs for 30 days. Export important ones.

## Optional: Custom Domain

If you want `greenie.mycompany.com`:

1. In Render → Web Service → **"Settings"**
2. Scroll to **"Custom Domain"**
3. Add your domain
4. Update DNS records (instructions provided)

## Cost Breakdown

| Service | Free Tier | Starter |
|---------|-----------|---------|
| Web Service | $0 | $7/mo |
| PostgreSQL | $0 (500 MB) | $15/mo (2 GB) |
| Groq API | $0 (30 req/min) | $0 (scale as needed) |
| **Total** | **$0** | **$22/mo** |

⭐ **You can run everything free!** (with slight limitations)

## Next Steps

1. ✅ Deploy to Render (this guide)
2. 📊 Monitor logs & metrics
3. 🚀 Share the chat URL with your team!
4. 💬 Collect feedback
5. 📈 Scale if needed

## Support

- **Render Docs**: https://render.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Groq API**: https://console.groq.com/docs
- **Your deployed app docs**: `https://greenie-xxxxx.onrender.com/docs`

---

**Ready to deploy?** Start with Step 1, follow the checklist, and you'll have Greenie live in 10 minutes! 🚀
