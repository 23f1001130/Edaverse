# Dataflow Deployment Guide (DigitalOcean Droplet)

This guide covers deploying Dataflow on a DigitalOcean droplet using Nginx + Systemd.

## Initial Setup (First Time)

### 1. Create a Droplet
- OS: Ubuntu 22.04 LTS or latest
- Size: $6/month (1GB RAM, 1 vCPU) minimum
- Region: Choose closest to your users
- Add SSH key during creation

### 2. SSH into Droplet
```bash
ssh root@your_droplet_ip
```

### 3. Run Setup Script
```bash
cd /tmp
git clone https://github.com/23f1001130/dataflow.git
cd dataflow
chmod +x deploy/setup.sh
./deploy/setup.sh
```

This script will:
- Install Python, Node, Nginx, Git
- Clone your repo to `/var/www/dataflow`
- Setup Python venv and install dependencies
- Build React frontend
- Configure Nginx as reverse proxy
- Create Systemd service for auto-restart

### 4. Verify It's Working
```bash
# Check backend service
systemctl status dataflow

# Check Nginx
nginx -t
systemctl status nginx

# Visit your configured domain in browser
https://your-domain.com
```

---

## Deployments (After Initial Setup)

### Quick Redeploy
Once initial setup is done, use the deploy script for future updates:

```bash
ssh root@your_droplet_ip
cd /var/www/dataflow && git pull && cd frontend && npm install --legacy-peer-deps && VITE_API_URL="" VITE_APP_URL="https://your-domain.com" npm run build && cp -r dist/* /var/www/html/dataflow/ && systemctl restart dataflow
```

Or run the deploy script:
```bash
/var/www/dataflow/deploy/deploy.sh
```

### What the Deploy Script Does
1. Pulls latest code from Git (`main` branch)
2. Updates backend Python dependencies
3. Rebuilds React frontend
4. Copies built files to Nginx directory
5. Restarts the backend service

---

## Directory Structure on Droplet

```
/var/www/dataflow/              # Main repo (git pull here)
  ├── backend/                  # FastAPI app
  │   ├── app/
  │   ├── venv/                 # Python virtual env
  │   └── requirements.txt
  ├── frontend/                 # React app
  │   ├── src/
  │   ├── dist/                 # Built on local machine
  │   └── package.json
  └── deploy/
      ├── deploy.sh             # Redeploy script
      ├── setup.sh              # Initial setup
      ├── nginx.conf
      └── dataflow.service

/var/www/html/dataflow/         # Nginx serves built frontend from here
/etc/nginx/sites-enabled/dataflow    # Nginx config (symlink)
/etc/systemd/system/dataflow.service # Auto-restart service
```

---

## Environment Variables

Frontend env vars are used at build time:

```bash
cd /var/www/dataflow/frontend
VITE_API_URL="" VITE_APP_URL="https://your-domain.com" npm run build
```

Set `VITE_APP_URL` to your real production domain before building. Also add the same domain in the Clerk dashboard under allowed origins/redirect URLs and email link settings. If Clerk only knows the droplet IP, verification emails can show the IP address.

Backend env vars can be set in `/etc/systemd/system/dataflow.service`:

```ini
[Service]
Environment="OLLAMA_URL=http://localhost:11434"
Environment="APP_ENV=production"
Environment="AUTH_TRUST_UNVERIFIED_JWT=false"
Environment="CLERK_ISSUER_URL=https://your-clerk-issuer.clerk.accounts.dev"
# Only needed when the frontend is hosted on a different origin:
Environment="CORS_ALLOWED_ORIGINS=https://your-domain.com"
```

Then restart: `systemctl restart dataflow`

For production auth, set either `CLERK_ISSUER_URL` or `CLERK_JWKS_URL` so the API verifies Clerk JWT signatures. Leave `TRUST_PROXY_AUTH_HEADERS=false` unless a trusted reverse proxy is injecting user identity headers.

---

## Monitoring & Troubleshooting

### View Logs
```bash
# Backend service logs
journalctl -u dataflow -f

# Nginx logs
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
```

### Check Backend Status
```bash
systemctl status dataflow
systemctl restart dataflow
systemctl stop dataflow
```

### Check Frontend Build
```bash
# Verify files are there
ls -la /var/www/html/dataflow/

# Test Nginx config
nginx -t
systemctl restart nginx
```

### Troubleshoot Service Issues
```bash
# Check if port 8000 is in use
netstat -tuln | grep 8000

# Test backend directly
curl http://localhost:8000/docs

# Restart with verbose output
systemctl restart dataflow
journalctl -u dataflow --no-pager -n 50
```

---

## HTTPS Setup (Recommended)

Install certbot for free HTTPS:
```bash
apt-get install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

Then update Nginx config in `/etc/nginx/sites-available/dataflow` to use SSL.

---

## Backup Data

Backend uploads go to:
```bash
/var/www/dataflow/backend/data/datasets/
```

Backup regularly:
```bash
tar -czf backup-$(date +%Y%m%d).tar.gz /var/www/dataflow/backend/data/
```

---

## Scaling Notes

For higher load:
- Increase workers in `dataflow.service`: `--workers 4` (depends on CPU cores)
- Add caching layer (Redis)
- Use CDN for frontend assets (Cloudflare, DigitalOcean Spaces)
- Consider managed database for data persistence

---

## SSH Key Deployment

To avoid entering password on redeploys, use SSH keys:
```bash
# On local machine
ssh-keygen -t ed25519

# Add public key to droplet
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@your_droplet_ip

# Test (should not ask for password)
ssh root@your_droplet_ip "echo Success"
```

Then you can add this to your CI/CD or shell alias:
```bash
alias deploy-dataflow='ssh root@your_droplet_ip "/var/www/dataflow/deploy/deploy.sh"'
```

---

## Database Persistence

Currently data is stored in `/var/www/dataflow/backend/data/`. If you need persistent storage:

1. **DigitalOcean Volumes**: Attach a persistent volume to droplet
2. **PostgreSQL/MySQL**: Migrate from file storage to managed database

For now, ensure you backup this directory regularly.
