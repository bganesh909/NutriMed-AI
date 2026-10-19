.PHONY: help up down build logs test test-backend test-ocr test-frontend seed clean models dev-local stop-local

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

build: ## Build all services
	docker compose build

logs: ## Tail logs from all services
	docker compose logs -f

logs-api: ## Tail API gateway logs
	docker compose logs -f api-gateway

logs-worker: ## Tail Celery worker logs
	docker compose logs -f celery-worker

test: ## Run all test suites (backend + OCR service + frontend)
	$(MAKE) test-backend
	$(MAKE) test-ocr
	$(MAKE) test-frontend

test-backend: ## Run backend tests (needs MongoDB + Redis running)
	cd backend && python -m pytest tests/ -v

test-unit: ## Run backend unit tests only
	cd backend && python -m pytest tests/unit/ -v

test-integration: ## Run backend integration tests only (needs MongoDB)
	cd backend && python -m pytest tests/integration/ -v

test-ocr: ## Run OCR service tests
	cd services/ocr-service && python -m pytest tests/ -v

test-frontend: ## Run frontend unit tests
	cd frontend && npm test

seed: ## Seed the database
	cd seeds && python seed_data.py

models: ## Pull Ollama models
	./infrastructure/scripts/init-ollama.sh

clean: ## Remove all containers, volumes, and images
	docker compose down -v --rmi local

dev-backend: ## Run backend in development mode
	cd backend && DEBUG=true uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run frontend in development mode
	cd frontend && npm run dev

dev: ## Run both backend and frontend in development
	$(MAKE) dev-backend & $(MAKE) dev-frontend

dev-local: ## Start the full stack locally without Docker (Ollama, OCR, API, Celery, frontend)
	./scripts/dev-local.sh

stop-local: ## Stop services started by dev-local (leaves Mongo/Redis/Ollama running)
	-pkill -f "uvicorn app.main:app" 2>/dev/null
	-pkill -f "celery -A app.core.celery_app" 2>/dev/null
	-pkill -f "next dev" 2>/dev/null
	@echo "Stopped backend, OCR, celery, and frontend."

status: ## Show status of all services
	docker compose ps

restart: ## Restart all services
	docker compose restart

mongo-shell: ## Open MongoDB shell
	docker compose exec mongo mongosh -u admin -p nutrimed_secret

redis-cli: ## Open Redis CLI
	docker compose exec redis redis-cli

rabbit-ui: ## Open RabbitMQ Management (prints URL)
	@echo "RabbitMQ Management: http://localhost:15672 (nutrimed/nutrimed_secret)"
