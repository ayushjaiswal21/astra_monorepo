#!/usr/bin/env bash
# One-time setup for an Oracle Cloud "Always Free" VM (Ubuntu 22.04/24.04)
# to run this app's Celery worker + Redis broker, so course generation stays
# genuinely async even though the free Render tier can't run a background
# worker. Run this once on a fresh instance, as a non-root user with sudo.
#
# shortcut: this script assumes you've already created the Always Free VM
# in the Oracle Cloud console (free tier: 2 AMD VM.Standard.E2.1.Micro
# instances, or 1 Ampere A1 instance with up to 4 OCPUs/24GB — either is
# plenty for Redis + one Celery worker), opened port 22 for SSH, and have
# cloned this repo onto it. Do that first; this script does not create the
# VM itself, and can't — that needs your own Oracle Cloud account.
set -euo pipefail

REPO_DIR="${1:-$HOME/astra_monorepo}"
APP_DIR="$REPO_DIR/astra"

echo "==> Installing Redis and Python build deps"
sudo apt-get update -y
sudo apt-get install -y redis-server python3-venv python3-pip build-essential libpq-dev

echo "==> Enabling Redis to start on boot, bound to localhost only"
sudo sed -i "s/^bind .*/bind 127.0.0.1 -::1/" /etc/redis/redis.conf
sudo systemctl enable redis-server
sudo systemctl restart redis-server

echo "==> Creating a Python venv for the Celery worker"
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Writing a systemd unit for the Celery worker"
sudo tee /etc/systemd/system/astra-celery.service > /dev/null <<EOF
[Unit]
Description=Astra Celery worker (course generation)
After=network.target redis-server.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/celery -A astralearn worker --loglevel=info --concurrency=2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "==> Enabling and starting the worker"
sudo systemctl daemon-reload
sudo systemctl enable astra-celery
sudo systemctl restart astra-celery

cat <<'EOF'

==> Done. Next steps:

1. Create $APP_DIR/.env on this VM with at least:
     CELERY_BROKER_URL=redis://127.0.0.1:6379/0
     GEMINI_API_KEY=...
     OLLAMA_URL=http://127.0.0.1:11434/api/generate   (only if you also install Ollama on this VM)
     DATABASE_URL=...   (point this at the SAME Postgres your Render web service uses,
                          e.g. a Neon.tech connection string, so the worker writes to the
                          same DB the web app reads from)

2. Point your Render web service's CELERY_BROKER_URL at this VM's public IP instead of
   127.0.0.1 (redis://<VM_PUBLIC_IP>:6379/0), and open port 6379 in the Oracle Cloud
   security list/NSG for that VM — restrict it to Render's outbound IP range if possible,
   never leave 6379 open to the whole internet with no auth. Redis has no password set by
   default here; for anything beyond a personal project, set `requirepass` in redis.conf
   and the matching password in the broker URL.

3. Check the worker is alive: `sudo systemctl status astra-celery` and
   `redis-cli ping` (should reply PONG).

4. (Optional, only if you want Ollama's real structure-generation path to run instead of
   the Gemini-only fallback) install Ollama on this same VM:
     curl -fsSL https://ollama.com/install.sh | sh
     ollama pull phi3:mini
   then set OLLAMA_URL to this VM's local address in the .env above.
EOF
