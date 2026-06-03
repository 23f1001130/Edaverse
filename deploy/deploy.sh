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
VITE_API_URL="" npm run build

# Copy frontend build to nginx directory
cp -r dist/* /var/www/html/dataflow/

# Restart backend service
sudo systemctl restart dataflow

echo "=== Deploy complete ==="
