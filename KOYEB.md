# SHEDS POS - Koyeb Hosting Guide

## What You Get (Free Tier)
- **1 service** with 256MB RAM / 1 vCPU
- **Free PostgreSQL database** (optional, we use SQLite)
- **Free TLS/HTTPS** included
- **No credit card required**
- **Sleeps after 30 minutes** of inactivity (app restarts automatically on next request)

## Deployment Steps

### Option A: Via Web (Easiest - No CLI)

1. **Push code to GitHub**
```bash
cd "C:\Users\Danzona 4\Downloads\DANZONA PHARM NIG LTD STORE"
git init
git add .
git commit -m "Initial commit"
# Create a repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/sheds-pos.git
git push -u origin main
```

2. **Sign up for Koyeb**
- Go to https://app.koyeb.com/auth/signup
- Sign up with GitHub (no credit card)
- Verify your email

3. **Create a Service**
- Click **"Create Service"**
- Select **"Dockerfile"**
- Connect your GitHub repo
- Select the repo you just pushed
- Koyeb will auto-detect `koyeb.yaml`

4. **Configure**
- **Instance type:** Free
- **Port:** 5000
- **Regions:** fra (Frankfurt) or iad (Washington DC)

5. **Deploy**
- Click **"Deploy"**
- Wait 3-5 minutes for build
- Your app will be live at: `https://sheds-pos-YOUR_USERNAME.koyeb.app`

### Option B: Via CLI

1. **Install Koyeb CLI**
```bash
# Windows (PowerShell)
iwr https://raw.githubusercontent.com/koyeb/koyeb-cli/master/install.ps1 -UseBasicParsing | iex

# Or via npm
npm install -g @koyeb/cli
```

2. **Authenticate**
```bash
koyeb auth login
```

3. **Deploy**
```bash
koyeb deploy -f koyeb.yaml
```

## Database Setup

### SQLite (Default - Simple)
The app uses SQLite by default. The database file is stored at `/data/danzona_pos.db`.

**Important:** Koyeb's filesystem is **ephemeral** by default. Data will be lost when the service restarts.

### To Persist Data on Koyeb:

1. **Add a Persistent Volume** (Free tier doesn't include persistent volumes)
   - Upgrade to paid tier ($2.40/month) for persistent storage

2. **Alternative: Use Koyeb PostgreSQL** (Free)
   - Create a free PostgreSQL database in Koyeb dashboard
   - Update your app to use PostgreSQL via `DATABASE_URL`

3. **Alternative: Backup regularly**
   - Use the app's export features
   - Download database weekly

## Keep App Awake

Free tier apps sleep after 30 minutes. To keep awake:

1. Go to https://uptimerobot.com (free)
2. Add new monitor:
   - **URL:** `https://sheds-pos-YOUR_USERNAME.koyeb.app/api/health`
   - **Interval:** 5 minutes
3. Add your email for alerts

## Custom Domain (Optional)

1. Go to Koyeb Dashboard → Service → Domains
2. Add your domain
3. Update DNS:
   - Type: CNAME
   - Name: `yourdomain.com`
   - Value: `sheds-pos-YOUR_USERNAME.koyeb.app`

## Update App

When you update your code:
```bash
git push
# Koyeb auto-redeploys if connected to GitHub
```

Or via CLI:
```bash
koyeb deploy -f koyeb.yaml
```

## Environment Variables

Set these in Koyeb Dashboard → Service → Environment:

| Variable | Value |
|----------|-------|
| SECRET_KEY | `openssl rand -hex 16` output |
| DB_PATH | `/data/danzona_pos.db` |
| PORT | `5000` |

## Troubleshooting

**App won't start:**
- Check logs in Koyeb Dashboard
- Make sure port 5000 is exposed
- Verify environment variables are set

**Database lost after restart:**
- Free tier has ephemeral storage
- Upgrade to paid tier for persistent volume
- Or switch to PostgreSQL

**App sleeping:**
- Use UptimeRobot to ping every 5 minutes
- Consider upgrading to hobby tier ($2.40/month) for always-on
