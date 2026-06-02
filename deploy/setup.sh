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
mkdir -p /var/www/dataflow-backend
mkdir -p /var/www/dataflow-frontend

# Clone repo into both locations (same repo, different purposes)
REPO_URL="REPLACE_WITH_YOUR_GITHUB_REPO_URL"

git clone $REPO_URL /var/www/dataflow-backend
git clone $REPO_URL /var/www/dataflow-frontend

# Setup Python backend
cd /var/www/dataflow-backend/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create data directory
mkdir -p /var/www/dataflow-backend/backend/data/datasets
chown -R www-data:www-data /var/www/dataflow-backend/backend/data

# Move backend app to correct location
cp -r /var/www/dataflow-backend/backend/* /var/www/dataflow-backend/
python3 -m venv /var/www/dataflow-backend/venv
/var/www/dataflow-backend/venv/bin/pip install -r /var/www/dataflow-backend/requirements.txt

# Build frontend
cd /var/www/dataflow-frontend/frontend
npm install --legacy-peer-deps
VITE_API_URL="" npm run build
cp -r dist/* /var/www/dataflow/

# Setup nginx
cp /var/www/dataflow-backend/deploy/nginx.conf /etc/nginx/sites-available/dataflow
ln -sf /etc/nginx/sites-available/dataflow /etc/nginx/sites-enabled/dataflow
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# Setup systemd service
cp /var/www/dataflow-backend/deploy/dataflow.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable dataflow
systemctl start dataflow

echo "=== Setup complete ==="
echo "Visit http://$(curl -s ifconfig.me) to see your app"
