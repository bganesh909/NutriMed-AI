#!/usr/bin/env bash
#
# dev-local.sh — start the full NutriMed AI stack locally WITHOUT Docker.
#
# Starts (in order, with health checks):
#   MongoDB, Redis  (via Homebrew services if not already listening)
#   Ollama          (ollama serve; pulls the model if missing)
#   OCR service     (:8001)
#   Backend API     (:8000, FastAPI)
#   Celery worker   (Redis broker)
#   Frontend        (:3000, Next.js)  -- runs in the foreground
#
# Ctrl+C stops everything this script started. Background logs go to ./logs/.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

OLLAMA_MODEL="${OLLAMA_MODEL:-mistral:7b}"
PIDS=()

# --- pretty logging ---------------------------------------------------------
c_blue=$'\033[34m'; c_green=$'\033[32m'; c_yellow=$'\033[33m'; c_red=$'\033[31m'; c_reset=$'\033[0m'
info()  { printf "%s==>%s %s\n" "$c_blue"   "$c_reset" "$*"; }
ok()    { printf "%s ok%s  %s\n" "$c_green"  "$c_reset" "$*"; }
warn()  { printf "%swarn%s %s\n" "$c_yellow" "$c_reset" "$*"; }
err()   { printf "%serr %s %s\n" "$c_red"    "$c_reset" "$*"; }

# --- helpers ----------------------------------------------------------------
port_open() { lsof -tiTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

wait_http() { # url label [timeout_s]
  local url="$1" label="$2" timeout="${3:-60}" i=0
  while (( i < timeout )); do
    if curl -fs -o /dev/null --max-time 2 "$url"; then ok "$label is up ($url)"; return 0; fi
    sleep 1; ((i++))
  done
  err "$label did not become healthy within ${timeout}s ($url). See logs/$label.log"
  return 1
}

start_bg() { # name command...
  local name="$1"; shift
  info "starting $name ..."
  ( exec "$@" ) >"$LOG_DIR/$name.log" 2>&1 &
  local pid=$!
  PIDS+=("$pid")
  printf '%s' "$pid" >"$LOG_DIR/$name.pid"
}

cleanup() {
  echo
  info "shutting down ..."
  # Kill in reverse start order.
  for (( idx=${#PIDS[@]}-1; idx>=0; idx-- )); do
    kill "${PIDS[$idx]}" 2>/dev/null || true
  done
  # Best-effort kill of child trees we know about.
  pkill -P $$ 2>/dev/null || true
  ok "stopped services started by this script (Ollama/Mongo/Redis left running)"
}
trap cleanup INT TERM EXIT

# --- 1. MongoDB + Redis (datastores) ---------------------------------------
if port_open 27017; then ok "MongoDB already running (:27017)"
else info "starting MongoDB via brew ..."; brew services start mongodb-community >/dev/null 2>&1 || warn "could not start MongoDB via brew — start it manually"; fi

if port_open 6379; then ok "Redis already running (:6379)"
else info "starting Redis via brew ..."; brew services start redis >/dev/null 2>&1 || warn "could not start Redis via brew — start it manually"; fi

# --- 2. Ollama --------------------------------------------------------------
if port_open 11434; then ok "Ollama already running (:11434)"
else start_bg ollama ollama serve; wait_http "http://localhost:11434/api/tags" ollama 30; fi

# Capture into a var first: piping into `grep -q` would SIGPIPE `ollama list`
# and (under `set -o pipefail`) wrongly report the model as missing.
installed_models="$(ollama list 2>/dev/null || true)"
if [[ "$installed_models" == *"${OLLAMA_MODEL%%:*}"* ]]; then
  ok "Ollama model present: $OLLAMA_MODEL"
else
  info "pulling Ollama model $OLLAMA_MODEL (one-time, large download) ..."
  ollama pull "$OLLAMA_MODEL"
fi

# --- 3. OCR service (:8001) -------------------------------------------------
# NOTE: services are launched from their OWN directory (not --app-dir). The
# backend's Pydantic settings use env_file=".env" relative to CWD; running from
# backend/ (where no .env exists) keeps it on its defaults (db nutrimed_ai, which
# holds the seed data). Running from repo root would load the root .env and
# switch databases / fail to parse ALLOWED_ORIGINS.
if port_open 8001; then warn "port 8001 busy — assuming OCR service already running"
else start_bg ocr bash -c "cd '$ROOT/services/ocr-service' && exec venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001"; fi
wait_http "http://localhost:8001/health" ocr 40

# --- 4. Backend API (:8000) -------------------------------------------------
if port_open 8000; then warn "port 8000 busy — assuming backend already running"
else start_bg backend bash -c "cd '$ROOT/backend' && exec venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"; fi
wait_http "http://localhost:8000/health" backend 40

# --- 5. Celery worker -------------------------------------------------------
start_bg celery bash -c "cd '$ROOT/backend' && exec venv/bin/celery -A app.core.celery_app worker -l info -Q reports,ai,notifications -c 2"
sleep 3
if grep -q "ready" "$LOG_DIR/celery.log" 2>/dev/null; then ok "celery worker ready"; else warn "celery worker still starting — check logs/celery.log"; fi

# --- 6. Frontend (:3000) — foreground --------------------------------------
echo
ok "Stack is up:"
printf "     Frontend  http://localhost:3000\n"
printf "     Backend   http://localhost:8000/docs\n"
printf "     OCR svc   http://localhost:8001/health\n"
printf "     Logs      %s/{ollama,ocr,backend,celery}.log\n" "$LOG_DIR"
echo
info "starting frontend in the foreground (Ctrl+C stops everything) ..."
cd "$ROOT/frontend"
npm run dev
