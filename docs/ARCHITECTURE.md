# Architecture notes

## What actually runs

```
Next.js (:3000) ──► FastAPI API gateway (:8000) ──┬──► MongoDB (data + report files in GridFS)
                                                   ├──► Redis (cache + Celery broker)
                                                   ├──► LLM: Ollama (:11434) or an
                                                   │    OpenAI-compatible API (e.g. Groq)
                                                   └──► OCR service (:8001)
                                                            ▲
Celery worker ──────────────────────────────────────────────┘
```

The API gateway is a modular monolith. It implements nutrition maths, workout
generation, lab interpretation and PDF rendering **in-process**
(`app/services/*.py`). Every LLM call goes through `app/services/llm_client.py`
(`LLM_PROVIDER`: `ollama` or `openai`), which sends only de-identified data.
Uploaded reports are stored encrypted in MongoDB GridFS
(`app/services/report_files.py`), so the API and the worker share no disk.
The only other network service it depends on is the OCR service.

## The `services/` directory

Only `ocr-service` remains, and it is the one the gateway actually calls.

The repository previously carried five further FastAPI apps (`llm`,
`nutrition`, `fitness`, `pdf`, `rag`) that nothing referenced -- no code path,
not even nginx. They were not simply duplicates: several held curated domain
data the running application lacked. Rather than delete that outright, the
valuable parts were **harvested into the gateway** and the empty shells removed:

| Harvested from | Now lives at | What it gives us |
|---|---|---|
| `fitness-service/exercise_database.py` | `app/data/exercise_database.py` | 81 exercises with form instructions, equipment, alternatives |
| `nutrition-service/food_database.py` | `app/data/food_database.py` | 113 foods with per-100g macros |
| `fitness-service/workout_generator.py` | `app/services/workout_templates.py` | Deterministic split/warm-up/cool-down generator |
| `nutrition-service/diet_generator.py` | `app/services/diet_templates.py` | Deterministic template meal plans |
| `nutrition-service/calculator.py` | `app/services/nutrition_calculator.py` | BMR / TDEE / macro / hydration functions |
| `pdf-service/chart_generator.py` | `app/services/chart_generator.py` | Biomarker, progress, macro and BMI charts |

Everything else (the five `main.py` / `config.py` / `schemas.py` sets and all of
`llm-service`, which merely wrapped the Ollama call the gateway already makes)
was deleted. It remains in git history if it is ever wanted back.

## Accuracy of generated plans

Diet and workout plans are produced by a local 7B model, which is good at
composition and unreliable at facts. Left alone it invents calorie counts and
exercise form cues -- unacceptable output for a health product. Three
mechanisms keep the output honest, in `app/services/plan_grounding.py`:

1. **Retrieval.** `select_foods` / `select_exercises` build a shortlist from
   the curated databases, filtered by dietary preference, allergies and
   fitness level, and ranked by the rule engine's findings (iron-rich foods
   when anemic, omega-3 when lipids are off, intensity capped when hemoglobin
   is low, cardio forced in when glucose is high).
2. **Constrained prompting.** The model may only use names from that
   shortlist, gives portions in grams, and is told explicitly that any
   calories, macros or form instructions it writes will be discarded.
3. **Verification.** `verify_diet_plan` recomputes every macro from
   grams x per-100g values; `verify_workout_plan` resolves each exercise
   against the catalogue and takes instructions from there. Names that do not
   resolve are dropped and logged. A typo is fuzzy-matched; a hallucination is
   removed.

If the model fails, times out, or nothing it produced survives verification,
`build_fallback_meal_plan` and `build_fallback_days` generate a complete plan
deterministically from the curated templates. A user is never shown an empty
plan, and never shown a number the system could have computed itself.

The same guard applies to the lab interpretation: `_drop_contradictions` in
`app/workers/analysis_worker.py` removes any AI statement calling a
rule-engine-flagged biomarker normal.

## OCR engines

The OCR service reads digital PDFs with `pdfplumber` and needs an OCR engine
only for images and scanned PDFs. It picks one at runtime:

1. **PaddleOCR** if importable (higher accuracy; no Apple Silicon wheel, so it
   lives in `requirements-paddle.txt`).
2. **Tesseract** via `pytesseract` otherwise — the default, and what
   `requirements.txt` installs. Needs the system binary
   (`brew install tesseract` / `apt-get install tesseract-ocr`).

`GET /health` reports the active engine in `ocr_engine`. If it returns `null`,
only digital PDFs can be processed.

## Keeping output accurate in production

The safeguards above fail *safe*, not *loud*: a broken model or a missing
dataset does not error, it quietly serves template plans to everyone. Three
things make that visible in a deployment.

### 1. Startup self-check

`app/services/grounding_selfcheck.py` runs on boot and validates that the
curated datasets loaded, cover the required categories and muscle groups, carry
form instructions, and that retrieval plus both fallbacks actually produce a
plan. Problems are logged at ERROR with an explicit "plan accuracy is DEGRADED"
line.

Application logging is configured in `app/main.py`. Without it only uvicorn's
access log reaches stdout and every one of these messages is discarded — which
is what made the degradation invisible in the first place.

### 2. `GET /health/ready`

`/health` stays a cheap liveness probe for container health checks.
`/health/ready` reports what accuracy actually depends on:

```json
{
  "status": "degraded",
  "degraded": ["llm"],
  "checks": {
    "mongodb": "ok",
    "grounding": {"ok": true, "foods": 113, "exercises": 81, "problems": []},
    "llm": {"provider": "ollama", "model": "mistral:7b", "status": "model_not_available", "available": ["llama3:latest"]},
    "ocr": {"status": "ok", "engine": "tesseract"},
    "generation_quality": {"window_days": 7, "kinds": {"diet": {"llm_verified": 40, "template_fallback": 2, "fallback_rate": 0.048}}}
  }
}
```

Point monitoring at this, not at `/health`.

### 3. Generation metrics

Every diet and workout generation writes one document to
`generation_metrics` recording the outcome:

| Outcome | Meaning |
|---|---|
| `llm_verified` | Model output used as-is; passed verification and the adequacy gate |
| `llm_repaired` | Used, but some items were dropped as unresolvable |
| `template_fallback` | Model output unusable; the deterministic template was served |
| `failed` | Nothing could be produced |

**A rising `fallback_rate` is the signal to investigate.** It means the model is
no longer contributing and users are receiving generic template plans. Common
causes: `OLLAMA_MODEL` naming a model that was never pulled, Ollama out of
memory, a timeout that is too low for the hardware, or a hosted provider's
rate limits (free tiers) or an expired API key.

### Configuration that must be right

| Variable | Why it matters |
|---|---|
| `OLLAMA_MODEL` | With `LLM_PROVIDER=ollama`: must name a model Ollama has actually pulled. If not, every plan falls back silently. Set explicitly in `.env` and compose; `init-ollama.sh` pulls it. |
| `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | With `LLM_PROVIDER=openai`: the hosted API (e.g. Groq). `/health/ready` checks the key works and the model is listed. |
| `LLM_TIMEOUT_SECONDS` | Default 300. A 7B model on CPU needs minutes for the longer prompts; too low means permanent fallback. |
| `LOG_LEVEL` | Default INFO. Below this the degradation warnings disappear. |

### Known deployment caveat

`docker-compose.yml` runs the API with `--reload` and bind-mounts `./backend`
into the container. That is a development configuration: the image contents are
shadowed by the mount, and `--reload` should not be used in production. A real
deployment wants a compose override (or a separate file) that drops both.

## Session handling

Access tokens expire after `JWT_EXPIRY_MINUTES` (default 30). The frontend
holds the refresh token in `localStorage` and the access token in both
`localStorage` (for the `Authorization` header) and a cookie (so `proxy.ts` can
guard routes server-side).

`src/lib/api.ts` refreshes transparently: on a 401 it exchanges the refresh
token, retries the original request once, and only redirects to `/login` if the
refresh itself fails. Requests that race into a 401 together wait on a single
refresh rather than triggering a stampede. Auth endpoints are excluded, so a
failed login or a failed refresh cannot loop.

### Known limitation: refresh tokens are not revoked

`POST /auth/refresh` issues a new pair, but the **old refresh token remains
valid** until it expires (7 days). Verified:

```
refresh with the rotated-away token -> 200
```

So a leaked refresh token stays usable for up to a week even after the
legitimate user has refreshed, and logging out clears the client only.

Fixing this needs server-side token state — either a denylist of used refresh
tokens (Redis, keyed by `jti`, expiring with the token) or a per-user token
version bumped on logout. The `jti` claim added to `create_access_token` is
what such a denylist would key on. Worth doing before this handles real
patient data outside a trusted network.
