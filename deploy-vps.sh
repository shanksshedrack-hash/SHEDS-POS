#!/bin/bash
set -e

echo "=========================================="
echo "  SHEDS POS - VPS Auto Deploy"
echo "=========================================="

APP_NAME="sheds-pos"
APP_DIR="/opt/sheds-pos"
DB_FILE="danzona_pos.db"
NGINX_CONF="/etc/nginx/sites-available/sheds-pos.conf"

# 1. Check root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./deploy-vps.sh)"
    exit 1
fi

# 2. Install dependencies
echo "[1/7] Installing dependencies..."
apt-get update -qq
apt-get install -y -qq docker.io docker-compose nginx curl > /dev/null 2>&1
systemctl enable docker
systemctl start docker
systemctl enable nginx
systemctl start nginx

# 3. Create app directory
echo "[2/7] Setting up app directory..."
mkdir -p "$APP_DIR"
mkdir -p "$APP_DIR/data"

# 4. Copy files
echo "[3/7] Copying application files..."
cp -r . "$APP_DIR/"
cd "$APP_DIR"

# 5. Setup environment
echo "[4/7] Configuring environment..."
if [ ! -f .env ]; then
    SECRET_KEY=$(openssl rand -hex 32)
    cat > .env <<EOF
SECRET_KEY=${SECRET_KEY}
DB_PATH=/app/data/${DB_FILE}
PORT=5000
EOF
fi

# 6. Deploy with Docker
echo "[5/7] Building and starting containers..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
docker-compose -f docker-compose.prod.yml up -d --build

# 7. Setup nginx
echo "[6/7] Configuring nginx..."
cp nginx.conf "$NGINX_CONF"
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/sheds-pos.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 8. Wait and verify
echo "[7/7] Verifying deployment..."
sleep 10
MAX_RETRIES=15
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:5000/api/health > /dev/null 2>&1; then
        echo ""
        echo "=========================================="
        echo "  DEPLOYMENT SUCCESSFUL!"
        echo "=========================================="
        PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null)
        echo "App URL:      http://${PUBLIC_IP}"
        echo "API Health:   http://${PUBLIC_IP}/api/health"
        echo "Data Dir:     ${APP_DIR}/data"
        echo ""
        echo "To enable HTTPS (recommended):"
        echo "  apt install certbot python3-certbot-nginx"
        echo "  certbot --nginx -d yourdomain.com"
        echo ""
        echo "To update app later:"
        echo "  cd ${APP_DIR} && git pull && docker-compose -f docker-compose.prod.yml up -d --build"
        echo ""
        exit 0
    fi
    RETRY=$((RETRY + 1))
    echo "Waiting... ($RETRY/$MAX_RETRIES)"
    sleep 3
done

echo ""
echo "WARNING: Health check did not pass in time"
echo "Check logs: docker logs sheds-pos-app"
exit 1

