# 🚀 Deploy Greenie to Render in 5 Steps

**Time to deploy: ~15 minutes**
**Cost: Free (or $7-22/month for production)**

## Step 1: Get Your API Keys (5 min)

### Get Groq API Key
1. Visit https://console.groq.com
2. Sign up for free
3. Go to Settings → API Keys
4. Copy your API key (starts with `gsk_`)
5. Save it somewhere safe

## Step 2: Prepare Your Code (2 min)

### Initialize Git
```bash
cd "path/to/Greenie"
git init
git add .
git commit -m "Greenie ready for deployment"
```

### Create GitHub Repo
1. Go to https://github.com/new
2. Name it `greenie`
3. Click "Create repository"
4. Follow the push instructions:
```bash
git remote add origin https://github.com/YOUR_USERNAME/greenie.git
git branch -M main
git push -u origin main
```

## Step 3: Create Render Account (2 min)

1. Go to https://render.com
2. Sign up (free)
3. Verify email
4. You're ready!

## Step 4: Deploy Web Service (3 min)

### In Render Dashboard:
1. Click **"New +"** → **"Web Service"**
2. Click **"Connect GitHub account"**
3. Select your `greenie` repo
4. Fill in:
   - **Name**: `greenie`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Select `Free` (or Starter for always-on)

5. Click **"Advanced"** and add Environment Variables:
   ```
   GROQ_API_KEY = gsk_your_key_here
   JWT_SECRET_KEY = your_super_secret_key_here_change_this
   ```

6. Click **"Create Web Service"**
7. Wait 2-3 minutes for first deployment
8. You'll see a green "Live" indicator when ready

## Step 5: Add PostgreSQL Database (3 min)

### In Render Dashboard:
1. Click **"New +"** → **"PostgreSQL"**
2. Name it `greenie-db`
3. Region: Same as web service (e.g., `Ohio`)
4. Plan: `Free` (500 MB included)
5. Click **"Create Database"**
6. Wait 2 minutes for DB to start

### Connect Database to Web Service:
1. Go back to your `greenie` **Web Service**
2. Click **"Environment"**
3. Scroll down → You should see `DATABASE_URL` pre-filled! ✅
4. If not, copy-paste it from the PostgreSQL database page
5. Your app auto-redeploys with the database

## ✅ Done! Your Chat is Live!

### Access Your Chat:
```
https://greenie-xxxxx.onrender.com/chat-ui
```

Replace `xxxxx` with your Render service name.

### Test It:
1. Open the URL in your browser
2. You should see the green chat button (💬)
3. Click it to open the popup
4. Sign up and start chatting!

### Share With Your Team:
Send them: `https://greenie-xxxxx.onrender.com/chat-ui`

They can:
- Sign up for free
- Chat with each other
- Chat with Greenie (powered by Groq API)
- Access from any device

## 📊 What You've Deployed

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  🌐 Web Service (Render)                                  │
│     • FastAPI server running 24/7 (or on-demand free)     │
│     • Handles chat requests                               │
│     • Auto-scales as needed                               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🗄️  PostgreSQL Database (Render)                         │
│     • Stores users, messages, memories                    │
│     • 500 MB free (grows only if needed)                  │
│     • Auto-backups (optional, paid tier)                  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🤖 LLM API (Groq)                                         │
│     • Powers AI responses                                 │
│     • Free tier: 30 requests/min (perfect for teams)      │
│     • No server needed - cloud API                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Monitor Your Deployment

### In Render Dashboard:
- **Logs**: See errors in real-time
- **Metrics**: CPU, RAM, bandwidth usage
- **Settings**: Change environment variables anytime

### Typical Issues & Fixes:
| Issue | Solution |
|-------|----------|
| App crashing | Check Logs tab, verify GROQ_API_KEY is set |
| Database error | Make sure DATABASE_URL is set |
| Chat not responding | Check Groq rate limits (30 req/min free tier) |
| Deploy failed | Check requirements.txt, python syntax |

## 💬 Update Your Code

After deployment, updating is easy:

```bash
# Make changes locally
# ... edit app.py, auth.py, etc ...

# Commit changes
git add .
git commit -m "Added feature XYZ"

# Push to GitHub
git push origin main

# Render automatically redeploys! ✅
# (Watch in Render dashboard for deployment status)
```

## 📈 Scale Up (When You Need More Power)

Current setup is great for:
- ✅ Teams of 5-20 people
- ✅ Casual chatting
- ✅ Learning & testing

To upgrade (optional):
- **Free → Starter**: $7/month (always on, faster cold starts)
- **PostgreSQL free → Starter**: $15/month (2 GB, backups)
- **Total**: ~$22/month for production-grade

## 🎉 You're Done!

Your Greenie chat is now:
- ✅ Live on the internet
- ✅ Accessible from any device
- ✅ Multi-user with authentication
- ✅ Powered by free Groq AI
- ✅ Using PostgreSQL database
- ✅ Costing $0/month

## 📚 Next Steps

1. **Share the URL** with your team
2. **Monitor logs** in Render dashboard
3. **Keep your JWT_SECRET_KEY secret** ✅
4. **Update code** whenever you want (auto-redeploys)
5. **Upgrade to Starter** if you want always-on service

## 🆘 Need Help?

- **Render Docs**: https://render.com/docs
- **Groq API**: https://console.groq.com/docs
- **API Docs** (live): `https://greenie-xxxxx.onrender.com/docs`
- **Chat UI** (live): `https://greenie-xxxxx.onrender.com/chat-ui`

---

**Congratulations! You've successfully deployed Greenie!** 🚀

Go forth and chat! 💬
