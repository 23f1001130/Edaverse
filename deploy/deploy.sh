#!/bin/bash
set -e
echo "=== Deploying Dataflow ==="

# Pull latest code from monorepo
cd /var/www/dataflow
git pull origin main

# Update backend dependencies
cd /var/www/dataflow/backend
source venv/bin/activate
pip install -r requirements.txt --quiet

# Build frontend
cd /var/www/dataflow/frontend
npm install --legacy-peer-deps --quiet
FRONTEND_APP_URL="${DATAFLOW_APP_URL:-${VITE_APP_URL:-}}"
if [ -z "$FRONTEND_APP_URL" ]; then
  echo "Warning: DATAFLOW_APP_URL/VITE_APP_URL is not set. Clerk emails and redirects may use the current host or droplet IP."
fi
VITE_API_URL="" VITE_APP_URL="$FRONTEND_APP_URL" npm run build

# Copy frontend build to nginx directory
cp -r dist/* /var/www/html/dataflow/

# Restart backend service
sudo systemctl restart dataflow

echo "=== Deploy complete ==="
