#!/bin/bash
set -e
echo "=== Setting up Dataflow on DigitalOcean ==="

# Update system
apt-get update -y
apt-get upgrade -y

# Install dependencies
apt-get install -y python3 python3-pip python3-venv nodejs npm nginx git

# Install Node 18+ via nvm if needed
node_version=$(node --version 2>/dev/null | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$node_version" -lt 18 ] 2>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

# Create directories
mkdir -p /var/www/dataflow
mkdir -p /var/www/html/dataflow

# Clone repo (monorepo with backend + frontend)
REPO_URL="https://github.com/23f1001130/dataflow"
git clone $REPO_URL /var/www/dataflow

# Setup Python backend
cd /var/www/dataflow/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create data directory
mkdir -p data/datasets
chown -R www-data:www-data data

# Build frontend
cd /var/www/dataflow/frontend
npm install --legacy-peer-deps
FRONTEND_APP_URL="${DATAFLOW_APP_URL:-${VITE_APP_URL:-}}"
if [ -z "$FRONTEND_APP_URL" ]; then
  echo "Warning: DATAFLOW_APP_URL/VITE_APP_URL is not set. Clerk emails and redirects may use the current host or droplet IP."
fi
VITE_API_URL="" VITE_APP_URL="$FRONTEND_APP_URL" npm run build
cp -r dist/* /var/www/html/dataflow/

# Setup nginx
cp /var/www/dataflow/deploy/nginx.conf /etc/nginx/sites-available/dataflow
ln -sf /etc/nginx/sites-available/dataflow /etc/nginx/sites-enabled/dataflow
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# Setup systemd service
cp /var/www/dataflow/deploy/dataflow.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable dataflow
systemctl start dataflow

# Set proper permissions
chown -R www-data:www-data /var/www/html/dataflow

echo "=== Setup complete ==="
echo "Visit your configured domain to see your app"
