#!/bin/bash
set -e

echo "=========================================="
echo "  SHEDS POS - Contabo VPS Deploy"
echo "=========================================="

# 1. Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# 2. Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 3. Generate strong secret key
SECRET_KEY=$(openssl rand -hex 32)
echo "Generated SECRET_KEY: $SECRET_KEY"

# 4. Create .env file
mkdir -p data
cat > .env <<EOF
SECRET_KEY=${SECRET_KEY}
DB_PATH=/app/data/danzona_pos.db
PORT=5000
EOF
echo "Created .env file"

# 5. Stop existing container if running
echo "Stopping existing container..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# 6. Build and start
echo "Building and starting container..."
docker-compose -f docker-compose.prod.yml up -d --build

# 7. Wait for container to start
echo "Waiting for app to start..."
sleep 8

# 8. Test health
MAX_RETRIES=10
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:5000/api/auth/check -H "X-API-Key: test" | grep -q "error"; then
        echo "âœ“ App is running (API responded)"
        break
    fi
    RETRY=$((RETRY + 1))
    echo "Waiting for app... ($RETRY/$MAX_RETRIES)"
    sleep 3
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo "âš  App may not be fully healthy yet. Checking logs..."
    docker logs danzona-pos --tail 20 2>/dev/null || true
fi

# 9. Get public IP
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo "App URL: http://${PUBLIC_IP}:5000"
echo "Data volume: $(pwd)/data"
echo ""
echo "Next steps:"
echo "1. Point your domain to ${PUBLIC_IP}"
echo "2. Install nginx: sudo apt install nginx"
echo "3. Copy nginx config: sudo cp nginx/conf.d/danzona-pos.conf /etc/nginx/sites-available/"
echo "4. Enable site: sudo ln -s /etc/nginx/sites-available/danzona-pos.conf /etc/nginx/sites-enabled/"
echo "5. Test nginx: sudo nginx -t && sudo systemctl reload nginx"
echo "6. Enable HTTPS: sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx -d yourdomain.com"
echo ""
echo "To update app later:"
echo "  git pull && docker-compose -f docker-compose.prod.yml up -d --build"
echo ""
