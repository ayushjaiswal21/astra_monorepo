# Deployment guide: astra_monorepo on Render.com (no credit card needed)

This is the free-tier-friendly alternative to `DEPLOYMENT.md` (which targets
a single Oracle Cloud VM with Docker Compose). Render's free plan doesn't
require a card, but it has real limits this guide works around:

- **No free background-worker service** - so this path does NOT use Celery.
  `astra`'s course generation runs synchronously instead (see the
  `CELERY_ENABLED=False` flag added for exactly this - the request just
  blocks until the course finishes generating, instead of running in the
  background).
- **Free web services sleep after ~15 minutes of inactivity** and take
  30-60s to wake up on the next request. Expected and fine for a student
  project/demo - not something this guide works around.
- **No free managed Postgres/Redis/Mongo on Render itself** (Render's free
  Postgres now expires after 30 days) - this guide uses three separate,
  genuinely-free-forever, no-card external services instead: **Neon**
  (Postgres), **MongoDB Atlas** (Mongo), and skips Redis entirely since
  Celery isn't used on this path.

## What you'll end up with

- 3 Render **Web Services** (Docker-based, using each app's existing
  `Dockerfile`): `asta-authentication`, `astra`, `ai-guru-backend`.
- 1 Render **Static Site** (always-free, no sleep): the `ai-guru` React
  frontend's production build.
- 1 free Neon Postgres project with **two separate databases** in it (one
  for `astra`, one for `asta_authentication`) - Neon lets you create
  multiple databases under one free project, so you don't need two
  separate Neon accounts/projects.
- 1 free MongoDB Atlas M0 cluster for `ai-guru`'s chat history/personalization.

## 1. Create the free external databases (no card for any of these)

**Neon** (https://neon.tech) - sign up, create one project. Inside it,
create two databases (Neon's dashboard has a "Databases" tab, or run
`CREATE DATABASE astra;` / `CREATE DATABASE asta_auth;` in its SQL editor
against the default database). Copy the two connection strings - they look
like:

```
postgresql://<user>:<password>@<host>.neon.tech/astra?sslmode=require
postgresql://<user>:<password>@<host>.neon.tech/asta_auth?sslmode=require
```

**MongoDB Atlas** (https://www.mongodb.com/cloud/atlas) - sign up, create a
free **M0** cluster (no card required for M0). Create a database user and
get the connection string:

```
mongodb+srv://<user>:<password>@<cluster>.mongodb.net/ai_guru_db?retryWrites=true&w=majority
```

Also in Atlas: Network Access -> allow access from `0.0.0.0/0` (Render's
outbound IPs aren't fixed on the free plan, so you can't allow-list a
specific IP - this is the standard tradeoff for a free-tier serverless host
talking to Atlas).

## 2. Create the 3 web services on Render

For each of `asta_authentication`, `astra`, `ai-guru/backend`: on Render,
**New -> Web Service**, connect this GitHub repo, set:

- **Root Directory**: the app's folder (`asta_authentication`, `astra`, or
  `ai-guru/backend`) - Render builds from that subdirectory.
- **Runtime**: Docker (it'll find the `Dockerfile` already in each folder).
- **Instance Type**: Free.

Then set each service's environment variables (Render's dashboard -> that
service -> Environment):

### `asta_authentication` env vars
```
DATABASE_URL=<Neon asta_auth connection string>
SECRET_KEY=<generate one: python -c "import secrets; print(secrets.token_hex(32))">
FLASK_DEBUG=false
SESSION_COOKIE_SECURE=true
ASTRALEARN_BASE_URL=https://<your-astra-service>.onrender.com
AI_GURU_BASE_URL=https://<your-ai-guru-backend-service>.onrender.com
AI_GURU_FRONTEND_BASE_URL=https://<your-ai-guru-frontend-static-site>.onrender.com
SSO_SHARED_SECRET=<one shared random value, same on all 3 services>
CORS_ALLOWED_ORIGINS=https://<your-astra-service>.onrender.com,https://<your-ai-guru-frontend-static-site>.onrender.com
```

### `astra` env vars
```
DATABASE_URL=<Neon astra connection string>
SECRET_KEY=<generate one>
DEBUG=False
ALLOWED_HOSTS=<your-astra-service>.onrender.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
USE_X_FORWARDED_PROTO=True
CELERY_ENABLED=False
GEMINI_API_KEY=<your real key>
OLLAMA_URL=                 # leave blank - no VM to run Ollama on in this path, Gemini-only
ASTRA_AUTH_BASE_URL=https://<your-asta-authentication-service>.onrender.com
AI_GURU_BASE_URL=https://<your-ai-guru-backend-service>.onrender.com
SSO_SHARED_SECRET=<the same shared value as above>
```

### `ai-guru-backend` env vars
```
GEMINI_API_KEY=<your real key>
MONGODB_URI=<Atlas connection string>
ALLOWED_ORIGINS=https://<your-astra-service>.onrender.com,https://<your-ai-guru-frontend-static-site>.onrender.com
SSO_SHARED_SECRET=<the same shared value as above>
```

Render gives you each service's `.onrender.com` URL only after the first
deploy - deploy once with placeholder URLs, then come back and fill in the
real ones once you know them, then redeploy (Render's "Manual Deploy" button).

## 3. One-time setup: migrations

Render's free Web Services don't give you a persistent shell by default,
but you can run one-off commands via Render's dashboard -> that service ->
"Shell" tab (available even on free, just not always-on):

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

`asta_authentication` creates its own tables on first boot (SQLAlchemy
`db.create_all()` in `app.py`) - no separate migration command needed.

## 4. Deploy the frontend as a Static Site

Render -> **New -> Static Site**, connect the repo, Root Directory
`ai-guru/frontend`, Build Command `npm install && npm run build`, Publish
Directory `build`. Add one env var available at build time:

```
REACT_APP_API_URL=https://<your-ai-guru-backend-service>.onrender.com
```

## 5. Verify

- Visit the `asta_authentication` service's URL, sign up/sign in.
- Visit `astra`'s URL, try creating a course - since `CELERY_ENABLED=False`,
  the request will just take a while (it's doing the AI call inline) and
  then return - that's expected on this path, not a bug.
- Visit the static site's URL, send a chat message.

## What this path explicitly does NOT give you (vs. the Oracle/Docker path)

- No free Ollama - there's no VM to install it on, so `astra` is
  Gemini-only here (quota limits apply directly, with no local fallback).
- No real background job queue - synchronous generation only.
- Free services sleep when idle and take a moment to wake up.
- Neon/Atlas free tiers have their own storage/compute limits - fine for a
  student project, not for real production traffic.

If/when you get real hosting credits (GitHub Student Pack, Azure for
Students, etc.) or a card, `DEPLOYMENT.md`'s Oracle Cloud + Docker Compose
path removes all of the above limits (real background workers, Ollama
running locally for free, no cold-start sleep, self-hosted DBs or your
choice of managed ones).
