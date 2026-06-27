.PHONY: help up down build logs test seed clean models

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

test: ## Run backend tests
	cd backend && python -m pytest tests/ -v

test-unit: ## Run unit tests only
	cd backend && python -m pytest tests/unit/ -v

test-integration: ## Run integration tests only
	cd backend && python -m pytest tests/integration/ -v

seed: ## Seed the database
	cd seeds && python seed_data.py

models: ## Pull Ollama models
	./infrastructure/scripts/init-ollama.sh

clean: ## Remove all containers, volumes, and images
	docker compose down -v --rmi local

dev-backend: ## Run backend in development mode
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run frontend in development mode
	cd frontend && npm run dev

dev: ## Run both backend and frontend in development
	$(MAKE) dev-backend & $(MAKE) dev-frontend

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
