# SHEDS POS - Hosting Guide

## Overview

SHEDS POS is a multi-tenant pharmacy management system. One hosted instance serves multiple pharmacies, each with isolated data via API keys.

## Quick Start: Register a New Pharmacy

1. Open the hosted app in a browser
2. Click **"New Pharmacy"** tab
3. Fill in pharmacy details and admin credentials
4. Save the **API key** shown after registration (required for login)
5. Login with admin username/password

## Deployment Options

### Option 1: Fly.io (Recommended - Always On, ~$5/month)

Best for always-on hosting with persistent storage.

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Deploy
fly launch
# When prompted, use existing fly.toml
fly secrets set SECRET_KEY=$(openssl rand -hex 32)
fly deploy
```

After deploy, your app URL will be: `https://sheds-pos-pharmacy.fly.dev`

To update: `git pull && fly deploy`

### Option 2: VPS (Contabo, DigitalOcean, etc.)

Best for dedicated server with full control.

```bash
# Upload project to VPS, then run:
sudo bash deploy-vps.sh
```

This will:
- Install Docker + Docker Compose + Nginx
- Build and start the app container
- Configure nginx reverse proxy
- Verify the app is running

Then point your domain to the VPS IP and enable HTTPS:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourpharmacy.com
```

To update the app:
```bash
cd /opt/sheds-pos && git pull && docker-compose -f docker-compose.prod.yml up -d --build
```

### Option 3: Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Deploy
railway login
railway init
railway up
```

Add a volume in Railway dashboard:
- Mount path: `/data`
- This persists the SQLite database

### Option 4: Render

1. Push code to GitHub
2. Connect Render to your repo
3. Render will use `render.yaml` automatically
4. The disk `sheds-data` persists the database

### Option 5: Docker (Local / Self-hosted)

```bash
# Create .env file
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
echo "DB_PATH=/data/danzona_pos.db" >> .env
echo "PORT=5000" >> .env

# Start
docker-compose -f docker-compose.prod.yml up -d --build

# Verify
curl http://localhost:5000/api/health
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Flask secret key (generate with `openssl rand -hex 32`) |
| `DB_PATH` | No | Path to SQLite database (default: `danzona_pos.db`) |
| `PORT` | No | Server port (default: `5000`) |
| `DATABASE_URL` | No | PostgreSQL URL (if set, uses Postgres instead of SQLite) |

## Database

- **SQLite (default)**: Single file database, easy backup. Best for single-server deployments.
- **PostgreSQL (optional)**: Set `DATABASE_URL` env var for production multi-instance setups.

### Backup SQLite Database

```bash
# Docker
docker cp sheds-pos-app:/data/danzona_pos.db ./backup-$(date +%Y%m%d).db

# VPS direct
cp /opt/sheds-pos/data/danzona_pos.db ./backup-$(date +%Y%m%d).db
```

## Security Notes

1. Always set a strong `SECRET_KEY` in production
2. Use HTTPS (certbot for VPS, Fly.io has built-in TLS)
3. Restrict database file permissions
4. Keep the server updated
5. Each pharmacy admin should keep their API key secure

## Architecture

```
Browser (HTML/CSS/JS)
    |
    | HTTP/HTTPS
    v
Nginx (reverse proxy, TLS termination) [VPS only]
    |
    | localhost
    v
Gunicorn + Flask (server.py)
    |
    | SQLite or PostgreSQL
    v
Database (danzona_pos.db)
```

## Support

For issues, check app logs:
```bash
# Docker
docker logs sheds-pos-app --tail 100

# VPS systemd
journalctl -u docker -f
```
