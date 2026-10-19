# NutriMed AI

AI-powered healthcare platform that combines lab report analysis, personalised nutrition planning, fitness programming, and supplement recommendations -- all running locally with privacy-first architecture.

## Architecture

```
                    +-------------------+
                    |   Next.js 16 SPA  |
                    |   (:3000)         |
                    +---------+---------+
                              |
                    +---------v---------+
                    | Nginx reverse     |
                    | proxy (:80)       |
                    +---------+---------+
                              |
                    +---------v---------+        +------------------+
                    | FastAPI gateway   +------->|  Ollama (:11434) |
                    | (:8000)           |        +------------------+
                    +--+-----+--------+-+
                       |     |        |          +------------------+
              +--------v-+ +-v-----+  +--------->| OCR svc (:8001)  |
              | MongoDB  | | Redis |       ^     +------------------+
              +----------+ +---+---+       |
                               |           |
                        +------v-------+   |
                        | Celery worker+---+
                        +--------------+
```

The API gateway is a modular monolith: nutrition, fitness, lab interpretation
and PDF generation run in-process, and it calls Ollama directly. The OCR
service is the only microservice it talks to.

Diet and workout plans are grounded in curated databases (113 foods, 81
exercises) and every macro and form instruction is verified against them
rather than trusted from the model, with deterministic template fallbacks when
generation fails. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Tech Stack

| Layer           | Technology                                           |
|-----------------|------------------------------------------------------|
| Frontend        | Next.js 16, TypeScript, Tailwind CSS, shadcn/ui      |
| API Gateway     | FastAPI (Python 3.11+), Pydantic v2                  |
| Database        | MongoDB 7 (motor async driver)                       |
| Cache           | Redis 7                                              |
| Message Queue   | RabbitMQ 3                                           |
| Task Queue      | Celery                                               |
| LLM             | Ollama (Llama 3, Mistral, etc.)                      |
| OCR             | Tesseract (default) or PaddleOCR (optional)          |
| PDF Generation  | ReportLab / WeasyPrint                               |
| Containerisation| Docker, Docker Compose                               |

## Prerequisites

- **Docker** and **Docker Compose** v2+
- **16 GB RAM** recommended (Ollama LLM models need 8 GB+)
- **Python 3.11+** (for local development without Docker)
- **Node.js 18+** and **npm/pnpm** (for frontend development)

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/nutrimed-ai.git
cd nutrimed-ai

# 2. Copy environment file and adjust values
cp .env.example .env

# 3. Start all services
docker compose up -d
```

The application will be available at:
- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000
- **API docs (Swagger):** http://localhost:8000/docs
- **RabbitMQ dashboard:** http://localhost:15672 (nutrimed / nutrimed_secret)

### Seed sample data

```bash
# With Docker
docker compose exec api-gateway python /app/../seeds/seed_data.py

# Or locally
cd seeds && python seed_data.py
```

### Pull Ollama models

```bash
# After Ollama container is running
docker compose exec ollama ollama pull mistral:7b
docker compose exec ollama ollama pull mistral
```

## Manual Setup (Development)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start MongoDB, Redis, RabbitMQ locally (or via Docker)
docker compose up -d mongo redis rabbitmq

# Run the API server. DEBUG=true is for local development only: among other
# things it lets the API start with the placeholder JWT_SECRET / AES_KEY.
DEBUG=true uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Celery Workers

```bash
cd backend
celery -A app.core.celery_app worker -l info -Q reports,ai,notifications -c 4
```

## API Documentation

See [docs/API.md](docs/API.md) for full endpoint documentation.

### Endpoint Summary

| Method | Path                              | Description                        |
|--------|-----------------------------------|------------------------------------|
| POST   | /api/v1/auth/register             | Register new user                  |
| POST   | /api/v1/auth/login                | Login and get tokens               |
| POST   | /api/v1/auth/refresh              | Refresh access token               |
| GET    | /api/v1/users/me                  | Get current user profile           |
| PUT    | /api/v1/users/me                  | Update profile                     |
| POST   | /api/v1/users/me/medical-profile  | Create/update medical profile      |
| POST   | /api/v1/reports/upload            | Upload lab report                  |
| GET    | /api/v1/reports/                  | List user reports                  |
| GET    | /api/v1/reports/{id}              | Get report details                 |
| POST   | /api/v1/reports/{id}/analyze      | Trigger report analysis            |
| GET    | /api/v1/reports/{id}/analysis     | Get analysis results               |
| POST   | /api/v1/nutrition/calculate       | Calculate nutrition targets        |
| POST   | /api/v1/nutrition/generate-diet   | Generate AI diet plan              |
| POST   | /api/v1/fitness/generate-workout  | Generate AI workout plan           |
| POST   | /api/v1/recommendations/generate  | Generate recommendations           |
| GET    | /api/v1/recommendations/          | List recommendations               |
| POST   | /api/v1/progress/                 | Log progress entry                 |
| GET    | /api/v1/progress/                 | Get progress history               |
| GET    | /api/v1/pdf/reports/{id}/pdf      | Download generated PDF report      |
| POST   | /api/v1/auth/forgot-password      | Email a password-reset link        |
| POST   | /api/v1/auth/reset-password       | Set a new password from the link   |
| POST   | /api/v1/auth/change-password      | Change password (signed in)        |
| DELETE | /api/v1/users/me                  | Delete account and all its data    |
| GET    | /api/v1/users/me/medical-profile  | Get medical profile                |
| DELETE | /api/v1/reports/{id}              | Delete a report and derived data   |
| GET    | /api/v1/nutrition/diet-plans      | Saved diet plans, newest first     |
| GET    | /api/v1/fitness/plans             | Saved workout plans, newest first  |
| GET    | /api/v1/notifications/            | Notifications and unread count     |
| POST   | /api/v1/notifications/{id}/read   | Mark one notification read         |
| POST   | /api/v1/notifications/read-all    | Mark all notifications read        |
| GET    | /api/v1/admin/stats               | Platform stats (admin)             |
| GET    | /api/v1/admin/users               | List/search users (admin)          |
| PATCH  | /api/v1/admin/users/{id}/role     | Change a user's role (admin)       |
| DELETE | /api/v1/admin/users/{id}          | Delete a user (admin)              |

## Project Structure

```
nutrimed-ai/
+-- backend/                   # FastAPI API Gateway
|   +-- app/
|   |   +-- api/v1/endpoints/  # Route handlers
|   |   +-- core/              # Config, security, database
|   |   +-- models/            # Pydantic MongoDB models
|   |   +-- schemas/           # Request/response schemas
|   |   +-- services/          # Business logic
|   |   +-- repositories/      # Data access layer
|   |   +-- middleware/        # Rate limiting, audit logging
|   |   +-- workers/           # Celery task definitions
|   |   +-- main.py            # App entry point
|   +-- tests/                 # pytest test suite
+-- frontend/                  # Next.js frontend
|   +-- src/
|       +-- app/               # Next.js app router pages
|       +-- components/        # React components
|       +-- hooks/             # Custom React hooks
|       +-- stores/            # Zustand state stores
|       +-- lib/               # Utilities, API client
+-- services/                  # Microservices
|   +-- ocr-service/           # OCR and biomarker extraction
|   +-- llm-service/           # Ollama LLM gateway
|   +-- nutrition-service/     # Nutrition calculations
|   +-- fitness-service/       # Workout generation
|   +-- rag-service/           # RAG with knowledge base
+-- shared/                    # Shared resources
|   +-- knowledge_base/        # Medical/nutrition reference data
|   +-- prompt_templates/      # LLM prompt templates
+-- seeds/                     # Sample data and seeding scripts
+-- docs/                      # Documentation
+-- infrastructure/            # Nginx, deployment configs
+-- docker-compose.yml         # Full stack orchestration
```

## Environment Variables

| Variable              | Default                                  | Description                              |
|-----------------------|------------------------------------------|------------------------------------------|
| MONGO_URI             | mongodb://localhost:27017                | MongoDB connection string                |
| MONGO_DB_NAME         | nutrimed_ai                              | Database name                            |
| REDIS_URL             | redis://localhost:6379/0                 | Redis connection URL                     |
| RABBITMQ_URL          | amqp://guest:guest@localhost:5672//      | RabbitMQ connection URL                  |
| JWT_SECRET            | (change in production)                   | JWT signing secret                       |
| JWT_ALGORITHM         | HS256                                    | JWT algorithm                            |
| JWT_EXPIRY_MINUTES    | 30                                       | Access token expiry                      |
| AES_KEY               | (change in production)                   | AES encryption key for reports           |
| OLLAMA_BASE_URL       | http://localhost:11434                   | Ollama API base URL                      |
| ALLOWED_ORIGINS       | http://localhost:3000,http://localhost:5173 | CORS allowed origins                  |

## Running Tests

```bash
cd backend

# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/ -v

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests (requires MongoDB and Redis)
pytest tests/integration/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing
```

## Deployment

- One Linux server with Docker Compose, nginx and a local model: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- Render + Vercel + MongoDB Atlas + Groq, defined in [render.yaml](render.yaml): [docs/DEPLOY_RENDER_VERCEL.md](docs/DEPLOY_RENDER_VERCEL.md)

## Troubleshooting

### MongoDB connection refused
Ensure MongoDB is running on port 27017. If using Docker:
```bash
docker compose up -d mongo
```

### Ollama models not loading
Check that the Ollama container has enough memory (8 GB+ recommended):
```bash
docker compose logs ollama
docker compose exec ollama ollama list
```

### Celery workers not processing tasks
Verify RabbitMQ is running and the worker is connected:
```bash
docker compose logs celery-worker
docker compose exec rabbitmq rabbitmqctl list_queues
```

### Frontend build errors
Clear Next.js cache and reinstall:
```bash
cd frontend
rm -rf .next node_modules
npm install
npm run dev
```

### Port conflicts
If ports 8000, 3000, 27017, 6379, 5672, or 11434 are in use, update port mappings in `docker-compose.yml`.

## License

MIT License. See [LICENSE](LICENSE) for details.
