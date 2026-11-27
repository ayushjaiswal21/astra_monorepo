# Deployment guide: astra_monorepo on a single VM

This guide gets all three apps — `asta_authentication` (Flask SSO hub, port
5000), `astra` (Django "AstraLearn" course platform, port 8000), and
`ai-guru` (FastAPI backend port 8001 + React frontend via nginx, port 3000)
— running together on one fresh Ubuntu VM (Oracle Cloud Free Tier or any
other provider) using `docker-compose.yml` at the repo root.

It gets the stack **running correctly on one VM**. It is explicitly **not**
a hardened, multi-server production architecture — see "What this guide
does NOT cover" at the end before you put real users on this.

---

## 1. Provision the VM

- Any Ubuntu 22.04/24.04 VM with at least 2 vCPU / 4GB RAM (you're running
  3 app containers + Postgres x2 + Redis + Mongo + nginx on one box).
- Open inbound ports in the VM's firewall / Oracle Cloud Security List:
  `22` (SSH), `5000` (asta_authentication), `8000` (astra), `8001`
  (ai-guru backend API), `3000` (ai-guru frontend). Oracle Cloud VMs need
  rules added in **both** the Security List/NSG *and* the VM's own
  `iptables`/`ufw` — a common cause of "port open in console but
  unreachable" on OCI.

## 2. Install Docker + Docker Compose

SSH into the VM, then:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Docker's official install script (installs Docker Engine + the
# docker compose v2 plugin together)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Let your user run docker without sudo (log out/in after this)
sudo usermod -aG docker $USER
newgrp docker

docker --version
docker compose version
```

## 3. Clone the repo

```bash
git clone <your-repo-url> astra_monorepo
cd astra_monorepo
```

## 4. Set up each app's `.env`

Each app keeps its own full configuration in its own `.env` file (never
committed). Copy each app's example file and fill in real values:

```bash
cp asta_authentication/.env.example asta_authentication/.env
cp astra/.env.example astra/.env               # once the astra app provides one
cp ai-guru/backend/.env.example ai-guru/backend/.env
```

At minimum, set in each:
- `asta_authentication/.env` — `SECRET_KEY`, `JWT_SECRET_KEY` (long random
  values — `python -c "import secrets; print(secrets.token_hex(32))"`),
  Google OAuth client ID/secret if you use Google login.
- `astra/.env` — `SECRET_KEY`, `GEMINI_API_KEY`, `JUDGE0_API_KEY` if used.
- `ai-guru/backend/.env` — `GEMINI_API_KEY`.

Then copy the root-level compose example and fill it in too:

```bash
cp .env.example .env
```

In the root `.env`, set:
- `PUBLIC_HOST` — this VM's public IP or domain name. This is baked into
  the ai-guru React frontend **at build time** and used for
  browser-facing redirect URLs, because browsers can't resolve Docker
  service names.
- `POSTGRES_ASTRA_*` / `POSTGRES_AUTH_*` — real database credentials
  (don't ship the `change-me-...` defaults).
- `SSO_SHARED_SECRET` — one shared value. It **must be identical** to
  whatever `SSO_SHARED_SECRET` ends up set to inside `astra/.env`,
  `asta_authentication/.env`, and `ai-guru/backend/.env` — it's how SSO
  handoff tokens are signed and verified between the three apps. The
  simplest way to guarantee this: leave `SSO_SHARED_SECRET` **unset** in
  each app's own `.env` and let `docker-compose.yml`'s `environment:`
  override (sourced from the root `.env`) be the single source of truth.

### Important: hostnames change in Docker vs local dev

Each app's own `.env`/`.env.example` defaults point at `localhost` for the
other two services (`ASTRALEARN_BASE_URL=http://localhost:8000`,
`AI_GURU_BASE_URL=http://localhost:8001`, etc.) — that's correct for
running all three directly on one dev machine, but wrong inside Docker,
where each app is a separate container and `localhost` means "this
container only."

`docker-compose.yml` already overrides every server-to-server URL
(`ASTRA_AUTH_BASE_URL`, `AI_GURU_BASE_URL`, `ASTRALEARN_BASE_URL`,
`DATABASE_URL`, `CELERY_BROKER_URL`, `MONGODB_URI`) via its own
`environment:` block, pointed at the Docker service names
(`asta-authentication`, `astra-web`, `ai-guru-backend`, `postgres-astra`,
`postgres-auth`, `redis`, `mongo`). You do not need to edit those into each
app's `.env` yourself — the compose file's `environment:` section takes
precedence over `env_file:`. The one exception is anything that reaches a
visitor's **browser** (`AI_GURU_FRONTEND_BASE_URL`, `CORS_ALLOWED_ORIGINS`,
the React build's `REACT_APP_API_URL`) — those must stay a public
address (`PUBLIC_HOST`), never an internal service name, since the
browser is outside the Docker network.

## 5. Build and start the stack

```bash
docker compose up -d --build
```

This builds all 5 images (astra, asta_authentication, ai-guru backend,
ai-guru frontend, and the astra image reused for the celery worker) and
starts: `postgres-astra`, `postgres-auth`, `redis`, `mongo`, `astra-web`,
`astra-celery-worker`, `asta-authentication`, `ai-guru-backend`,
`ai-guru-frontend`.

## 6. One-time setup steps

Run Django migrations and collect static files (the `astra` container's
image has `manage.py`, so exec into the running `astra-web` container):

```bash
docker compose exec astra-web python manage.py migrate --noinput
docker compose exec astra-web python manage.py collectstatic --noinput
docker compose exec astra-web python manage.py createsuperuser
```

`asta_authentication` initializes its own tables on first run via
SQLAlchemy/Flask-Migrate — check that app's `init_db.py`/`migrate.py` for
whether a one-time init command is needed against the new Postgres DB; if
so, run it the same way:

```bash
docker compose exec asta-authentication python init_db.py
```

## 6b. Install Ollama on the VM (for free local course-generation AI)

`astra`'s course generation tries Ollama first, falling back to Gemini.
Ollama runs directly on the VM's host (not inside a container here, to
keep the Docker setup simpler) - install it once, pull a model, and point
`astra`'s `.env` at it:

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable --now ollama      # keeps it running after reboot
ollama pull llama3.2:3b                 # ~2GB, the model this project verified works well
```

Then in `astra/.env` (on the host, before `docker compose up`), set:

```bash
OLLAMA_URL=http://host.docker.internal:11434/api/generate
OLLAMA_MODEL=llama3.2:3b
```

`host.docker.internal` lets a container reach a service running on the VM
itself (not inside Docker) - if that hostname doesn't resolve on your
Docker version, use the VM's docker0 bridge IP instead (`ip addr show
docker0`, usually `172.17.0.1`) and set `OLLAMA_URL` to that IP.

Verify it's reachable from inside the container before relying on it:

```bash
docker compose exec astra-web curl -s http://host.docker.internal:11434/api/tags
```

If this returns `{"models":[...]}` with `llama3.2:3b` listed, course
generation will actually use it instead of falling straight through to
Gemini (whose free-tier quota is easy to exhaust - Ollama running locally
costs nothing per request and doesn't share that limit).

## 7. Verify it's up

```bash
docker compose ps
docker compose logs -f           # all services, follow mode
```

Hit each service from a browser or curl:
- `http://<PUBLIC_HOST>:5000` — asta_authentication
- `http://<PUBLIC_HOST>:8000` — astra
- `http://<PUBLIC_HOST>:8001/docs` — ai-guru backend (FastAPI auto-docs)
- `http://<PUBLIC_HOST>:3000` — ai-guru frontend

## 8. Troubleshooting

**A service won't start / keeps restarting:**
```bash
docker compose logs <service-name>          # e.g. astra-web, ai-guru-backend
docker compose ps                           # shows restart counts / health
```

**View logs for just one service, following:**
```bash
docker compose logs -f astra-celery-worker
```

**Restart just one service without touching the others:**
```bash
docker compose restart astra-web
```

**Rebuild just one service after a code change:**
```bash
docker compose up -d --build astra-web
```

**Database connection errors on startup:** `astra-web`/`astra-celery-worker`
and `asta-authentication` `depends_on` their Postgres service with a
`service_healthy` condition, so they should wait for Postgres to actually
accept connections — but if you still see connection errors, check
`docker compose logs postgres-astra` (or `postgres-auth`) for the DB
failing to start (often a bad `POSTGRES_PASSWORD` left unset, or a stale
volume from a previous password).

**Celery worker not picking up tasks:** confirm `astra-celery-worker` and
`astra-web` show the *same* `CELERY_BROKER_URL` (`redis://redis:6379/0` —
set by compose, not whatever `astra/.env` has) with
`docker compose exec astra-celery-worker env | grep CELERY`, and that
`docker compose logs redis` shows Redis accepting connections.

**SSO handoff/login redirects fail between apps:** almost always a
mismatched `SSO_SHARED_SECRET` between the three containers — check with
`docker compose exec <service> env | grep SSO_SHARED_SECRET` on each.

**Reset everything (destructive — wipes DB data):**
```bash
docker compose down -v
```

## What this guide does NOT cover

This gets the stack running correctly on one VM. It is **not**:

- **HTTPS/TLS or a real domain.** Everything above is plain HTTP on raw
  ports. For a real deployment, put a reverse proxy (Caddy, or
  nginx + certbot) in front of these four ports on 80/443 with a real
  domain name and automatic cert renewal. Not set up here.
- **A managed database.** `postgres-astra`, `postgres-auth`, and `mongo`
  are self-hosted containers on named volumes on this one VM — fine to
  start, but there's no replication, and if the VM's disk is lost, so is
  the data. For real production, consider a managed Postgres (e.g. OCI's
  managed DB service) and MongoDB Atlas instead, pointing `DATABASE_URL`
  / `MONGODB_URI` at them instead of the `postgres-*`/`mongo` services.
- **Backups.** Nothing here backs up the Postgres/Mongo volumes
  automatically. At minimum, schedule periodic `pg_dump`/`mongodump` to
  off-box storage before relying on this for real user data.
- **Horizontal scaling / multi-server.** This is one VM running every
  service as a single container each (one Django process, one Celery
  worker, etc). Fine for small/moderate load; it is not a
  load-balanced, multi-node setup.

## A note on the two Postgres databases

`astra` and `asta_authentication` each get their **own** Postgres
container (`postgres-astra`, `postgres-auth`) rather than sharing one
instance. Both apps already support `DATABASE_URL` (`astra` via
`dj-database-url`, `asta_authentication` reads it directly into its
SQLAlchemy URI) and both already ship `psycopg2-binary`, so giving
`asta_authentication` real Postgres parity with `astra` was a small,
already-supported step rather than leaving it on SQLite. Separate
containers (vs. one Postgres server with two databases) trade a little
extra RAM for simpler, fully independent credentials/volumes/restarts per
app — reasonable on a VM with a few GB of headroom; merge them into one
Postgres instance with two databases later if memory becomes tight.
