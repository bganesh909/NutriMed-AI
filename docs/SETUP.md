# NutriMed AI -- Detailed Setup Guide

## System Requirements

| Requirement        | Minimum            | Recommended         |
|--------------------|--------------------|---------------------|
| CPU                | 4 cores            | 8+ cores            |
| RAM                | 8 GB               | 16 GB+              |
| Disk               | 20 GB free         | 50 GB+ free         |
| OS                 | macOS 13+ / Ubuntu 22.04+ / Windows 11 (WSL2) | macOS 14+ / Ubuntu 24.04 |
| Docker             | 24.0+              | 25.0+               |
| Docker Compose     | v2.20+             | v2.27+              |
| Python             | 3.11               | 3.12                |
| Node.js            | 18 LTS             | 20 LTS              |

## Installing Docker

### macOS

```bash
# Install via Homebrew
brew install --cask docker

# Or download Docker Desktop from https://www.docker.com/products/docker-desktop/
# Then start Docker Desktop from Applications
```

### Ubuntu / Debian

```bash
# Remove old versions
sudo apt-get remove docker docker-engine docker.io containerd runc

# Install prerequisites
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg

# Add Docker GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add your user to docker group (log out and back in after)
sudo usermod -aG docker $USER
```

### Windows (WSL2)

1. Install WSL2: `wsl --install`
2. Download Docker Desktop: https://www.docker.com/products/docker-desktop/
3. Enable WSL2 integration in Docker Desktop settings

## Installing Ollama (Local Development)

Ollama allows running LLMs locally without Docker.

### macOS

```bash
# Install
brew install ollama

# Start the Ollama service
ollama serve

# Pull models (in a new terminal)
ollama pull llama3
ollama pull mistral
```

### Linux

```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Start the service
systemctl start ollama

# Pull models
ollama pull llama3
ollama pull mistral
```

### Verify

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Test a model
ollama run llama3 "Say hello"
```

## MongoDB Setup (Local Development)

### macOS

```bash
# Install via Homebrew
brew tap mongodb/brew
brew install mongodb-community@7.0

# Start MongoDB
brew services start mongodb-community@7.0

# Verify
mongosh --eval "db.adminCommand('ping')"
```

### Ubuntu

```bash
# Import public key
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
  sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

# Add repository
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
  https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | \
  sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Install and start
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod
```

### Docker only

```bash
docker compose up -d mongo
```

MongoDB will be available at `mongodb://localhost:27017`.

## Redis Setup (Local Development)

### macOS

```bash
brew install redis
brew services start redis
redis-cli ping  # should return PONG
```

### Ubuntu

```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
redis-cli ping
```

### Docker only

```bash
docker compose up -d redis
```

Redis will be available at `redis://localhost:6379`.

## RabbitMQ Setup (Local Development)

### macOS

```bash
brew install rabbitmq
brew services start rabbitmq

# Management UI at http://localhost:15672 (guest/guest)
```

### Ubuntu

```bash
sudo apt-get install rabbitmq-server
sudo systemctl start rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
```

### Docker only

```bash
docker compose up -d rabbitmq
```

Management UI: http://localhost:15672 (nutrimed / nutrimed_secret)

## Backend Development Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Install test dependencies
pip install pytest pytest-asyncio httpx

# Create .env file (copy from example or set variables)
cat > .env << 'EOF'
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=nutrimed_ai
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672//
JWT_SECRET=dev-secret-change-in-production
AES_KEY=dev-aes-key-change-in-production-32
OLLAMA_BASE_URL=http://localhost:11434
ALLOWED_ORIGINS=["http://localhost:3000"]
DEBUG=true
EOF

# Start the API server with auto-reload
uvicorn app.main:app --reload --port 8000

# In a separate terminal, start Celery workers
celery -A app.core.celery_app worker -l info -Q reports,ai,notifications -c 4
```

## Frontend Development Setup

```bash
cd frontend

# Install dependencies
npm install

# Create local environment
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
EOF

# Start development server with hot reload
npm run dev

# Build for production
npm run build
npm start
```

The frontend will be available at http://localhost:3000.

## Running Individual Services

Each microservice can be started independently for development:

```bash
# OCR Service
cd services/ocr-service
pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload

# LLM Service
cd services/llm-service
pip install -r requirements.txt
uvicorn app.main:app --port 8002 --reload

# Nutrition Service
cd services/nutrition-service
pip install -r requirements.txt
uvicorn app.main:app --port 8003 --reload

# Fitness Service (if it has a main.py)
cd services/fitness-service
pip install -r requirements.txt
uvicorn app.main:app --port 8004 --reload

# RAG Service
cd services/rag-service
pip install -r requirements.txt
uvicorn app.main:app --port 8006 --reload
```

## Running All Infrastructure via Docker (Services Locally)

A common development pattern: run databases and message queues in Docker, services locally.

```bash
# Start only infrastructure
docker compose up -d mongo redis rabbitmq ollama

# Then run the backend and frontend locally (see above)
```
