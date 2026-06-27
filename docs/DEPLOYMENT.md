# NutriMed AI -- Production Deployment Guide

## Overview

This guide covers deploying NutriMed AI to a production environment using Docker Compose with SSL, monitoring, and backups.

## Prerequisites

- A Linux server (Ubuntu 22.04+ recommended) with at least 16 GB RAM
- Domain name with DNS pointing to the server
- Docker and Docker Compose installed
- SSL certificate (or use Let's Encrypt)

## 1. Docker Compose Production Configuration

Create `docker-compose.prod.yml`:

```yaml
version: "3.9"

services:
  api-gateway:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports: []  # No direct port exposure; Nginx handles routing
    depends_on:
      mongo:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    env_file: .env.production
    volumes:
      - uploads_data:/app/uploads
    command: >
      gunicorn app.main:app
      --worker-class uvicorn.workers.UvicornWorker
      --workers 4
      --bind 0.0.0.0:8000
      --timeout 120
      --access-logfile -
    restart: always
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G
    networks:
      - nutrimed-internal

  celery-worker:
    build: ./backend
    depends_on:
      mongo:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    env_file: .env.production
    volumes:
      - uploads_data:/app/uploads
    command: celery -A app.core.celery_app worker -l warning -Q reports,ai,notifications -c 4
    restart: always
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G
    networks:
      - nutrimed-internal

  celery-beat:
    build: ./backend
    depends_on:
      redis:
        condition: service_healthy
    env_file: .env.production
    command: celery -A app.core.celery_app beat -l warning
    restart: always
    networks:
      - nutrimed-internal

  mongo:
    image: mongo:7
    volumes:
      - mongo_data:/data/db
      - ./infrastructure/mongo/mongod.conf:/etc/mongod.conf:ro
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_ROOT_USER}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_ROOT_PASSWORD}
    command: mongod --config /etc/mongod.conf --auth
    restart: always
    healthcheck:
      test: ["CMD", "mongosh", "-u", "${MONGO_ROOT_USER}", "-p", "${MONGO_ROOT_PASSWORD}", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4G
    networks:
      - nutrimed-internal

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    command: >
      redis-server
      --appendonly yes
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --requirepass ${REDIS_PASSWORD}
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - nutrimed-internal

  rabbitmq:
    image: rabbitmq:3-management
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    restart: always
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5
    networks:
      - nutrimed-internal

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    restart: always
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
        limits:
          memory: 8G
    networks:
      - nutrimed-internal

  frontend:
    build:
      context: ./frontend
      args:
        NEXT_PUBLIC_API_URL: https://${DOMAIN}/api/v1
    restart: always
    networks:
      - nutrimed-internal

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infrastructure/nginx/production.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
      - certbot_webroot:/var/www/certbot:ro
    depends_on:
      - api-gateway
      - frontend
    restart: always
    networks:
      - nutrimed-internal

volumes:
  mongo_data:
  redis_data:
  rabbitmq_data:
  ollama_data:
  uploads_data:
  certbot_webroot:

networks:
  nutrimed-internal:
    driver: bridge
```

## 2. Production Environment Variables

Create `.env.production`:

```bash
# Application
APP_NAME=NutriMed AI
DEBUG=false

# Domain
DOMAIN=nutrimed.example.com

# MongoDB
MONGO_URI=mongodb://nutrimed_user:STRONG_PASSWORD_HERE@mongo:27017/nutrimed_ai?authSource=admin
MONGO_DB_NAME=nutrimed_ai
MONGO_ROOT_USER=admin
MONGO_ROOT_PASSWORD=CHANGE_THIS_STRONG_PASSWORD

# Redis
REDIS_URL=redis://:REDIS_PASSWORD_HERE@redis:6379/0
REDIS_PASSWORD=CHANGE_THIS_REDIS_PASSWORD

# RabbitMQ
RABBITMQ_URL=amqp://nutrimed:RABBITMQ_PASSWORD@rabbitmq:5672//
RABBITMQ_USER=nutrimed
RABBITMQ_PASSWORD=CHANGE_THIS_RABBITMQ_PASSWORD

# JWT -- generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
JWT_SECRET=GENERATE_A_STRONG_SECRET_HERE
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=30

# AES -- generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
AES_KEY=GENERATE_A_STRONG_AES_KEY_HERE

# Ollama
OLLAMA_BASE_URL=http://ollama:11434

# CORS
ALLOWED_ORIGINS=["https://nutrimed.example.com"]
```

## 3. SSL/TLS Setup with Let's Encrypt

### Initial certificate

```bash
# Install certbot
sudo apt-get install certbot

# Get initial certificate
sudo certbot certonly --standalone -d nutrimed.example.com

# Certificate files will be at:
#   /etc/letsencrypt/live/nutrimed.example.com/fullchain.pem
#   /etc/letsencrypt/live/nutrimed.example.com/privkey.pem
```

### Auto-renewal

```bash
# Add to crontab
sudo crontab -e

# Renew twice daily, reload nginx after renewal
0 0,12 * * * certbot renew --quiet --deploy-hook "docker compose -f /path/to/docker-compose.prod.yml restart nginx"
```

## 4. Nginx Configuration

Create `infrastructure/nginx/production.conf`:

```nginx
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    sendfile    on;
    tcp_nopush  on;
    tcp_nodelay on;

    keepalive_timeout 65;
    client_max_body_size 50M;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
    limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/m;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name nutrimed.example.com;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    # HTTPS server
    server {
        listen 443 ssl http2;
        server_name nutrimed.example.com;

        ssl_certificate     /etc/letsencrypt/live/nutrimed.example.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/nutrimed.example.com/privkey.pem;
        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # API
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://api-gateway:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 120s;
        }

        # Auth endpoints with stricter rate limiting
        location /api/v1/auth/ {
            limit_req zone=auth burst=3 nodelay;
            proxy_pass http://api-gateway:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Health check
        location /health {
            proxy_pass http://api-gateway:8000;
        }

        # API docs (optional: disable in production)
        location /docs {
            return 404;
        }
        location /openapi.json {
            return 404;
        }

        # Frontend
        location / {
            proxy_pass http://frontend:3000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## 5. Backup Strategy

### MongoDB automated backups

```bash
#!/bin/bash
# backup_mongo.sh -- run daily via cron

BACKUP_DIR="/backups/mongo"
DATE=$(date +%Y%m%d_%H%M%S)
CONTAINER="nutrimed-ai-mongo-1"

mkdir -p "$BACKUP_DIR"

docker exec "$CONTAINER" mongodump \
  --username admin \
  --password "$MONGO_ROOT_PASSWORD" \
  --authenticationDatabase admin \
  --db nutrimed_ai \
  --out "/tmp/backup_$DATE"

docker cp "$CONTAINER:/tmp/backup_$DATE" "$BACKUP_DIR/backup_$DATE"
docker exec "$CONTAINER" rm -rf "/tmp/backup_$DATE"

# Compress
tar -czf "$BACKUP_DIR/backup_$DATE.tar.gz" -C "$BACKUP_DIR" "backup_$DATE"
rm -rf "$BACKUP_DIR/backup_$DATE"

# Retain last 30 days
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: backup_$DATE.tar.gz"
```

Add to crontab:

```bash
0 2 * * * /path/to/backup_mongo.sh >> /var/log/nutrimed-backup.log 2>&1
```

### Redis backup

Redis AOF persistence is enabled by default in the compose file. For periodic snapshots:

```bash
docker exec nutrimed-ai-redis-1 redis-cli -a "$REDIS_PASSWORD" BGSAVE
docker cp nutrimed-ai-redis-1:/data/dump.rdb /backups/redis/dump_$(date +%Y%m%d).rdb
```

## 6. Monitoring

### Health checks

The Docker Compose file includes built-in health checks. You can monitor externally:

```bash
# API health
curl -f https://nutrimed.example.com/health

# MongoDB
docker exec nutrimed-ai-mongo-1 mongosh --eval "db.adminCommand('ping')"

# Redis
docker exec nutrimed-ai-redis-1 redis-cli -a "$REDIS_PASSWORD" ping

# RabbitMQ
curl -u nutrimed:password http://localhost:15672/api/healthchecks/node
```

### Log aggregation

```bash
# View logs for all services
docker compose -f docker-compose.prod.yml logs -f

# View logs for a specific service
docker compose -f docker-compose.prod.yml logs -f api-gateway

# Export logs to file
docker compose -f docker-compose.prod.yml logs --no-color > /var/log/nutrimed-all.log
```

### Recommended monitoring stack

For production, consider adding:

- **Prometheus + Grafana** for metrics and dashboards
- **Loki** for log aggregation
- **Uptime Kuma** or **Healthchecks.io** for uptime monitoring
- **Sentry** for error tracking (add `SENTRY_DSN` to `.env.production`)

## 7. Scaling Considerations

### Horizontal scaling

```yaml
# Scale API workers
docker compose -f docker-compose.prod.yml up -d --scale api-gateway=3

# Scale Celery workers
docker compose -f docker-compose.prod.yml up -d --scale celery-worker=4
```

### MongoDB replica set

For high availability, convert MongoDB to a replica set:

```yaml
mongo-primary:
  image: mongo:7
  command: mongod --replSet rs0 --auth
  # ... configuration

mongo-secondary:
  image: mongo:7
  command: mongod --replSet rs0 --auth
  # ... configuration
```

### Redis Sentinel

For Redis high availability:

```yaml
redis-sentinel:
  image: redis:7-alpine
  command: redis-sentinel /etc/sentinel.conf
```

### Load balancing

When running multiple API instances, Nginx will round-robin by default. For session affinity (if needed):

```nginx
upstream api_backend {
    ip_hash;
    server api-gateway-1:8000;
    server api-gateway-2:8000;
    server api-gateway-3:8000;
}
```

## 8. Deployment Checklist

- [ ] Set strong passwords for all services in `.env.production`
- [ ] Generate unique JWT_SECRET and AES_KEY
- [ ] Configure SSL certificate
- [ ] Set up automated backups
- [ ] Configure firewall (only expose ports 80 and 443)
- [ ] Set DEBUG=false
- [ ] Disable /docs and /openapi.json endpoints
- [ ] Configure CORS to only allow production domain
- [ ] Set up monitoring and alerting
- [ ] Pull required Ollama models
- [ ] Run seed data script
- [ ] Test all endpoints
- [ ] Set up log rotation
