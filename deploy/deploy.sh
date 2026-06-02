#!/bin/bash
set -e
echo "=== Deploying Dataflow ==="

# Pull latest code
cd /var/www/dataflow-backend
git pull origin main

# Update backend dependencies
source venv/bin/activate
pip install -r requirements.txt --quiet

# Build frontend
cd /var/www/dataflow-frontend
git pull origin main
npm install --legacy-peer-deps --quiet
VITE_API_URL="" npm run build

# Copy frontend build to nginx directory
cp -r dist/* /var/www/dataflow/

# Restart backend
sudo systemctl restart dataflow

echo "=== Deploy complete ==="
