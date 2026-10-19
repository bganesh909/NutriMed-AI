# NutriMed AI — Local Setup (no Docker)

Quick-start for running the full stack on this Mac without Docker.
For the Docker-based / detailed guide, see [docs/SETUP.md](docs/SETUP.md).

> Always invoke tools as `venv/bin/<tool>` — don't `source venv/bin/activate`.
> The venv shebangs broke when the project moved to `~/Desktop`.

## Start order

Run each in its own terminal tab, from the project root (`~/Desktop/nutrimed-ai`).

### 1. MongoDB + Redis

```bash
brew services start mongodb-community
brew services start redis
```

Skip if already running (`lsof -iTCP:27017 -iTCP:6379 -sTCP:LISTEN`).

### 2. Ollama (local LLM)

```bash
ollama serve
```

Skip if the Ollama app is already running. Model used: `mistral:7b` (already pulled).

### 3. OCR service — port 8001

```bash
cd services/ocr-service && venv/bin/uvicorn app.main:app --port 8001
```

### 4. Backend API — port 8000

```bash
cd backend && DEBUG=true venv/bin/uvicorn app.main:app --reload --port 8000
```

`DEBUG=true` is for local development only: with no mail server configured,
password-reset emails (including the reset link) are written to the backend log
instead of being sent.

### 5. Celery worker (report processing)

```bash
cd backend && venv/bin/celery -A app.core.celery_app worker -l info -Q reports,ai,notifications -c 2
```

### 6. Frontend — port 3000

```bash
cd frontend && npm run dev
```

Open **http://localhost:3000** · API docs at **http://localhost:8000/docs**

## One command alternative

```bash
make dev-local    # starts steps 2–6, logs go to ./logs/
make stop-local   # stops OCR, backend, Celery, frontend
```

## Running on different ports (port clash)

If 8000/3000 are taken by another project, run the backend and frontend on other
ports and point them at each other with env vars (no code changes needed):

```bash
# Backend on 8010, allowing the frontend origin on 3010
cd backend && DEBUG=true ALLOWED_ORIGINS='["http://localhost:3010"]' venv/bin/uvicorn app.main:app --reload --port 8010

# Frontend on 3010, calling the backend on 8010
cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8010/api/v1 npx next dev -p 3010
```

`ALLOWED_ORIGINS` must be a JSON list. OCR (8001) and Celery are unchanged.

## Use Groq instead of local Ollama

Plans and analysis are much faster with a hosted model. Create
`backend/.env` (gitignored) with only these lines; the API and the Celery
worker both start from `backend/`, so both pick it up:

```bash
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_...            # from https://console.groq.com
LLM_MODEL=llama-3.3-70b-versatile
```

Restart the backend and the worker. Ollama is then not needed. Groq's free
tier has per-minute and per-day limits; when they are hit, the app falls back
to template plans. Only de-identified data is sent (no names, emails or report
files). Use test data, not real patients, on a free tier.

## Where things are

| Page | URL |
|---|---|
| Landing page (signed out) | `/` |
| Sign in / sign up / forgot password | `/login`, `/register`, `/forgot-password` |
| Terms, privacy & medical disclaimer | `/legal` |
| Admin console (admin accounts only) | `/admin` |

**Password reset locally:** request it at `/forgot-password`, then copy the link
from the backend log (`logs/backend.log` if you started it with `nohup`, or the
terminal running uvicorn). Links expire after 30 minutes and work once.

**Email in production:** set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
`SMTP_PASSWORD`, `SMTP_FROM` and `FRONTEND_URL` (see `.env.example`), and leave
`DEBUG` off.

## Test logins

| Role  | Email               | Password     |
|-------|---------------------|--------------|
| Admin | `admin@nutrimed.ai` | `Admin@1234` |
| User  | `test@nutrimed.ai`  | `Test@1234`  |
| User  | `rahul@example.com` | `Test@1234`  |
| User  | `priya@example.com` | `Test@1234`  |

## Health checks

```bash
curl localhost:11434/api/tags   # Ollama
curl localhost:8001/health      # OCR service
curl localhost:8000/health      # Backend
```

## Stopping on other ports

`make stop-local` stops *every* `uvicorn app.main:app` process, including other
projects' servers. When running on the alternate ports, stop NutriMed only:

```bash
pkill -f "port 8010"; pkill -f "port 8001"; pkill -f "next dev -p 3010"; pkill -f "celery -A app.core.celery_app"
```

## Notes

- AI calls run on CPU and are slow: workout plan ~80s, full report analysis ~5 min.
- The root `.env` is **not** loaded in local dev (backend runs from `backend/`, which has
  no `.env`), so config comes from `backend/app/core/config.py` defaults — database
  `nutrimed_ai`, which holds the seed data.
- Celery uses Redis (`redis://localhost:6379/1`) as its broker, not RabbitMQ.
- `DEBUG=true` also lets the API start with the built-in placeholder `JWT_SECRET`
  and `AES_KEY`. Without it the API refuses to start until both are replaced
  (see `docs/DEPLOYMENT.md`); that is intended for production.
- After changing worker code, restart the Celery worker; unlike uvicorn `--reload`
  it does not pick up changes on its own.
