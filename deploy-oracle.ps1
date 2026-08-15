param(
    [Parameter(Mandatory=$true)][string]$VpsIp,
    [Parameter(Mandatory=$true)][string]$KeyPath,
    [Parameter(Mandatory=$false)][string]$SshUser = 'ubuntu'
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path '.').Path
$Zip = Join-Path $Root 'danzona-pos-deploy.zip'

if (!(Test-Path -LiteralPath $Zip)) { throw 'danzona-pos-deploy.zip not found' }
if (!(Test-Path -LiteralPath $KeyPath)) { throw 'SSH key file not found' }
if (!(Get-Command ssh -ErrorAction SilentlyContinue)) { throw 'OpenSSH client not found. Install it with: winget install Microsoft.OpenSSH.Beta -e --source winget' }

$Target = "$SshUser@$VpsIp"
Write-Host "Uploading deployment package to $Target..."
scp -i $KeyPath $Zip "$Target`:~/"

$RemoteCommands = @'
set -e
cd ~
sudo mkdir -p /var/www/danzona-pos
sudo unzip -o danzona-pos-deploy.zip -d /var/www/danzona-pos

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx
else
  sudo dnf install -y python3 python3-pip python3-virtualenv nginx certbot python3-certbot-nginx
fi

cd /var/www/danzona-pos
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "Installing PostgreSQL..."
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql postgresql-contrib
else
  sudo dnf install -y postgresql-server postgresql-contrib
  sudo postgresql-setup initdb
fi
sudo systemctl enable --now postgresql

echo "Configuring PostgreSQL database..."
DB_PASSWORD=$(openssl rand -hex 16)
sudo -u postgres psql -c "CREATE USER danzona WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE danzona_pos OWNER danzona;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE danzona_pos TO danzona;"

SECRET_KEY=$(openssl rand -hex 32)

SERVICE_USER=$(whoami)
cat >/tmp/danzona-pos.service <<EOF
[Unit]
Description=SHEDS POS
After=network.target postgresql.service

[Service]
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=/var/www/danzona-pos
Environment="PATH=/var/www/danzona-pos/venv/bin"
Environment="SECRET_KEY=${SECRET_KEY}"
Environment="DATABASE_URL=postgresql://danzona:${DB_PASSWORD}@127.0.0.1:5432/danzona_pos"
ExecStart=/var/www/danzona-pos/venv/bin/gunicorn --bind 127.0.0.1:5000 server:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/danzona-pos.service /etc/systemd/system/danzona-pos.service
sudo systemctl daemon-reload
sudo systemctl enable danzona-pos
sudo systemctl restart danzona-pos

cat >/tmp/danzona-pos-nginx <<'EOF'
server {
    listen 80;
    server_name _;

    root /var/www/danzona-pos;
    index sales.html;

    location / {
        try_files $uri $uri/ /sales.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo mv /tmp/danzona-pos-nginx /etc/nginx/sites-available/danzona-pos
if [ -e /etc/nginx/sites-enabled/default ]; then sudo rm -f /etc/nginx/sites-enabled/default; fi
sudo ln -sf /etc/nginx/sites-available/danzona-pos /etc/nginx/sites-enabled/danzona-pos
sudo nginx -t
sudo systemctl restart nginx

mkdir -p /var/www/danzona-pos/data
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/bin/pg_dump -U danzona -h 127.0.0.1 danzona_pos > /var/www/danzona-pos/data/backup-\$(date +\%Y\%m\%d).sql 2>/dev/null") | crontab
echo "Daily PostgreSQL backup cron added"

echo 'Deployment completed. Open http://YOUR_VPS_IP/sales.html. Add your domain later and run certbot if needed.'
'@

Write-Host "Running remote deployment on $Target..."
ssh -i $KeyPath $Target $RemoteCommands
