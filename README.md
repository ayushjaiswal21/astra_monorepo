# Astra — AI-Powered Learning & Professional Networking Ecosystem

A single sign-on ecosystem of three connected products: a LinkedIn-style
professional network built for students/educators, an AI course-generation
LMS, and an AI mentor chatbot — sharing one identity layer across all three.

**Live:**
- Auth / Network hub: https://asta-authentication.onrender.com
- AstraLearn (courses): https://astra-web-txuw.onrender.com
- AI Guru chat (frontend): https://ai-guru-frontend.onrender.com
- AI Guru backend (API docs): https://ai-guru-backend-v7q3.onrender.com/docs

*(Render appends a random suffix to a service's URL if the exact name is
already taken by another account - check your own Render dashboard if
these don't match after a redeploy.)*

---

## What this is

Three independently-deployable apps, one shared login:

| App | Stack | What it does |
|---|---|---|
| **`asta_authentication`** | Flask + Socket.IO | The identity hub. Sign up once, use everywhere. LinkedIn-style profile, networking, jobs/internships/events, real-time chat, groups, a career-path recommendation quiz. |
| **`astra`** | Django + Celery | AstraLearn - type a topic, get a full AI-generated course (modules, lessons, quizzes). Difficulty adapts to how you're actually doing. |
| **`ai-guru`** | FastAPI + React | An AI mentor chatbot with document-grounded answers (RAG), streaming responses, voice input/output, and image chat. |

A short-lived signed token (`SSO_SHARED_SECRET`) lets the auth hub hand off a
logged-in session to either of the other two apps without a second login.

---

## Features

### Astra Auth (the hub)
- Profile (education, experience, skills, certifications) with real CRUD
- Connections/networking, real-time chat (Socket.IO)
- Jobs, internships, workshops, events - post, apply, register, with real
  applicant tracking
- Groups - create, join, post
- A LinkedIn-style post feed: like, comment, repost, send-as-DM, saved items
- News feed (manually curated + live API articles)
- **Career GPS**: an embedding-based quiz that ranks real career paths
  against your stated skills/interests (not a hardcoded lookup table)
- AI-generated learning paths, with one markable "active" path
- A real password-reset flow (token-based, with an email fallback)
- Analytics dashboard, dark mode, a consistent design system site-wide

### AstraLearn (course generation)
- **Multi-provider AI pipeline with automatic failover**: tries Ollama
  (free, local) first, falls back to OpenRouter (free, no card) if that's
  unavailable, falls back to Gemini last - a single point of failure in any
  one provider never takes the feature down
- **Adaptive difficulty**: a lightweight mastery-scoring model tracks how
  you do on quizzes and feeds that back into the next generated content's
  difficulty level
- A from-scratch-pruned, fine-tuned **local Transformer model** (11.9M
  params, ~48MB) as a free, offline fallback for lesson simplification when
  no external AI is reachable
- Lesson pages with Content / Simplified / Example / Quiz tabs, plus
  text-to-speech ("read aloud")
- Comprehensive test generation (MCQs + coding problems)
- Per-course ownership and permission checks

### AI Guru (mentor chatbot)
- **Streaming chat** - responses render progressively, not as one block
- **RAG**: index documents, get answers grounded in them, with a lexical
  fallback that works even without a live embeddings API or a database
- Voice input (browser speech recognition) and voice output
  (text-to-speech "Listen" button on every response)
- Image-based chat
- Session-aware personalization (remembers your preferred response style)

---

## Architecture

```
                     ┌─────────────────────┐
                     │   asta_authentication│  (the SSO hub)
                     │   Flask · :5000       │
                     └──────────┬───────────┘
                     signed SSO │ handoff token
              ┌──────────────────┴──────────────────┐
              ▼                                      ▼
     ┌─────────────────┐                   ┌─────────────────┐
     │  astra (Django)  │  ── cross-app ──▶ │  ai-guru backend │
     │  AstraLearn       │     AI calls     │  FastAPI · :8001 │
     │  :8000            │                   └────────┬────────┘
     └──────────────────┘                             │
                                             ┌─────────▼────────┐
                                             │ ai-guru frontend  │
                                             │ React (static)    │
                                             └───────────────────┘

Each app owns its own database (Postgres in production, SQLite locally).
AstraLearn's AI pipeline: Ollama → OpenRouter → Gemini (first one that
answers wins). ai-guru's RAG store is a local vector store (not tied to
MongoDB's uptime); MongoDB (when configured) adds persistent chat history.
```

---

## Tech stack

**Backends:** Flask, Django, FastAPI · **Frontend:** React, server-rendered
Jinja/Django templates · **Databases:** PostgreSQL (Neon), MongoDB Atlas,
SQLite (local dev) · **AI/ML:** Google Gemini, Ollama (local LLMs),
OpenRouter, a custom pruned-and-fine-tuned encoder-decoder Transformer
(PyTorch/HuggingFace), retrieval-augmented generation · **Real-time:**
Flask-SocketIO, FastAPI streaming responses · **Infra:** Docker,
Docker Compose, Render.com, Celery + Redis (background jobs)

---

## Repo layout

```
astra_monorepo/
├── asta_authentication/   # Flask auth/network hub
├── astra/                 # Django course platform (AstraLearn)
├── ai-guru/
│   ├── backend/            # FastAPI chatbot + RAG + local transformer
│   └── frontend/           # React chat UI
├── docker-compose.yml      # Run all 3 apps + databases together
├── render.yaml             # One-click Render.com Blueprint deploy
├── DEPLOYMENT.md           # Deploy guide: single VM + Docker Compose
└── RENDER_DEPLOYMENT.md    # Deploy guide: Render free tier, no card needed
```

---

## Running it locally

Each app has its own `requirements.txt`/`package.json` and `.env.example`.
Quick version (see each app's own README/`.env.example` for the full list
of env vars):

```bash
# 1. asta_authentication
cd asta_authentication && pip install -r requirements.txt
cp .env.example .env   # fill in real values
python app.py          # http://localhost:5000

# 2. astra
cd astra && pip install -r requirements.txt
cp .env.example .env
python manage.py migrate && python manage.py runserver   # http://localhost:8000

# 3. ai-guru backend
cd ai-guru/backend && pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8001

# 4. ai-guru frontend
cd ai-guru/frontend && npm install && npm start   # http://localhost:3000
```

Or run everything at once with `docker-compose.yml` (needs Docker) - see
`DEPLOYMENT.md`. To deploy for free without a credit card, see
`RENDER_DEPLOYMENT.md` and `render.yaml` (one-click Render Blueprint).

---

## Known limitations

- Render's free tier sleeps services after ~15 minutes idle (expect a
  30-60s cold start on the first request after a gap).
- The local Transformer fallback is a genuine from-scratch fine-tune, not a
  production-grade model - it generalizes correctly but output fluency is
  rough compared to Gemini/OpenRouter.
- Course generation is synchronous (not backgrounded) on the free-hosting
  path, since free tiers typically don't offer a background-worker service.
