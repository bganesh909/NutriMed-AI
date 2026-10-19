# NutriMed AI -- Production Deployment Guide

NutriMed AI runs on a single Linux server with Docker Compose, behind nginx
with a Let's Encrypt certificate. GitHub Actions builds the images and deploys
over SSH.

## 1. What runs where

`docker-compose.yml` is the development setup; `docker-compose.prod.yml` layers
the production settings on top of it. Always pass both files:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml <command>
```

| Service | Role | Reachable from the internet |
|---|---|---|
| nginx | TLS, routing (`/api` and `/health` to the API, everything else to the app), rate limits | **Yes, ports 80 and 443 only** |
| frontend | Next.js app | No |
| api-gateway | FastAPI | No (only through nginx) |
| celery-worker | Report pipeline and on-request plans | No |
| ocr-service | Text extraction from reports | No |
| ollama | Local LLM (GPU); not needed with a hosted model such as Groq | No |
| mongo | Database, with a root user from `.env` | No |
| redis | Celery broker, rate limiting | No |

Uploaded reports are stored encrypted with `AES_KEY` in MongoDB (GridFS), so
the API and the worker need no shared disk and the database backup includes
them. RabbitMQ and celery-beat are not started in production (Celery uses
Redis; there are no periodic tasks).

## 2. Prerequisites

- **Server:** Ubuntu 22.04 or 24.04 with an NVIDIA GPU (for example AWS
  `g4dn.xlarge`, GCP `g2-standard-4`, Azure `NC4as_T4_v3`), 16 GB RAM, 4 vCPUs,
  50 GB+ disk. Pick a region that meets your data-residency obligations.
  Without a GPU the app still works, but plans take minutes and diet plans often
  fall back to templates (see section 5).
- **Docker Engine** with the **Compose plugin v2.24.4 or newer**
  ([install guide](https://docs.docker.com/engine/install/ubuntu/)).
- **GPU servers:** the NVIDIA driver and the
  [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
  Check with `sudo docker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi`.
- **A domain** with an A record pointing at the server.
- **An email provider** with SMTP access (Amazon SES, Postmark, SendGrid, ...)
  for password-reset emails.

Firewall: allow SSH, 80 and 443 only.

```bash
sudo ufw allow OpenSSH && sudo ufw allow 80,443/tcp && sudo ufw enable
```

## 3. Configure

```bash
sudo mkdir -p /opt/nutrimed-ai && sudo chown "$USER" /opt/nutrimed-ai
git clone https://github.com/bganesh909/NutriMed-AI.git /opt/nutrimed-ai
cd /opt/nutrimed-ai
cp .env.example .env
chmod 600 .env
```

Edit `.env`. Generate each secret with
`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`.

| Variable | Value |
|---|---|
| `DEBUG` | `false` (the production file forces it off anyway) |
| `JWT_SECRET`, `AES_KEY` | Two different generated values. With `DEBUG=false` the API refuses to start on placeholders, values under 32 characters, or identical values. |
| `DOMAIN` | `app.example.com` (no `https://`) |
| `MONGO_ROOT_USERNAME`, `MONGO_ROOT_PASSWORD` | Database root user. URL-safe characters only; the API's `MONGO_URI` is built from them. |
| `ALLOWED_ORIGINS` | `["https://app.example.com"]` (a JSON list) |
| `FRONTEND_URL` | `https://app.example.com` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | From your email provider |
| `OLLAMA_MODEL` | `mistral:7b` unless you choose another model |
| `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | Optional: a hosted model instead of Ollama, e.g. Groq (`openai`, `https://api.groq.com/openai/v1`, your key, `llama-3.3-70b-versatile`). Then add `--scale ollama=0`. Only de-identified data is sent. Free tiers are rate-limited, and some providers' terms let them use what you send to train models; for real patients use a paid plan whose terms rule that out. |

> **Keep `AES_KEY` and `JWT_SECRET` in a password manager.** Uploaded reports
> are encrypted with `AES_KEY`; if it is lost or changed, they cannot be read.

## 4. TLS certificate

Install certbot (the snap package is current; Ubuntu's apt package may be too
old for `reconfigure`):

```bash
sudo snap install --classic certbot
sudo mkdir -p /var/www/certbot
```

Get the first certificate **before** starting the stack, while port 80 is free:

```bash
sudo certbot certonly --standalone -d app.example.com -m you@example.com --agree-tos --no-eff-email
```

Once the stack is running (section 5), switch renewals to the webroot nginx
serves, so they work without stopping nginx, and reload nginx after each
renewal:

```bash
sudo certbot reconfigure --cert-name app.example.com --webroot --webroot-path /var/www/certbot
sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh > /dev/null <<'EOF'
#!/bin/sh
cd /opt/nutrimed-ai && docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T nginx nginx -s reload
EOF
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
sudo certbot renew --dry-run
```

## 5. Start

Either build the images on the server:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

or run the images the CD workflow pushed (section 8). Packages of a private
repository need a registry login first, with a personal access token that has
`read:packages`:

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u <github-user> --password-stdin
export IMAGE_TAG=<short commit SHA or version>
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

No GPU? Add `-f docker-compose.cpu.yml` to every command.

Load the model (once; it is kept in the `ollama_data` volume):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec ollama ollama pull mistral:7b
```

Check it:

```bash
curl -fsS https://app.example.com/health
curl -fsS https://app.example.com/health/ready   # mongodb, llm and ocr should be "ok"
```

## 6. Create the admin account

**Never run the seed script (`seeds/seed_data.py`) in production:** it creates
accounts whose passwords are published in the repository.

Register normally at `https://app.example.com/register`, then promote that
account (replace the email; `nutrimed` is `MONGO_DB_NAME`):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec mongo sh -c \
  'mongosh --quiet -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin nutrimed \
   --eval "db.users.updateOne({email: \"you@example.com\"}, {\$set: {role: \"admin\"}})"'
```

Sign out and back in; the Admin console appears in the sidebar.

## 7. Backups

Back up the database (it includes the uploaded reports, stored in GridFS) and
copy the archives off the server (for example to object storage). Save as
`/opt/nutrimed-ai/backup.sh` and run it daily from root's crontab
(`0 2 * * * /opt/nutrimed-ai/backup.sh`):

```bash
#!/bin/sh
set -e
cd /opt/nutrimed-ai
BACKUP_DIR=/var/backups/nutrimed
STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Database: one compressed archive of all databases.
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T mongo sh -c \
  'mongodump --quiet -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --archive --gzip' \
  > "$BACKUP_DIR/mongo_$STAMP.archive.gz"

find "$BACKUP_DIR" -type f -mtime +30 -delete
```

Restore the database with
`... exec -T mongo sh -c 'mongorestore -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --archive --gzip --drop' < mongo_<stamp>.archive.gz`,
which restores the uploaded reports with it. Redis holds only
queues and rate-limit counters and needs no backup.

## 8. Continuous deployment (GitHub Actions)

`.github/workflows/cd.yml` builds the `api-gateway`, `frontend` and
`ocr-service` images, pushes them to GHCR tagged with the short commit SHA,
then deploys over SSH: it checks out that commit in `/opt/nutrimed-ai`, logs
the server in to GHCR, and runs `pull` and `up -d` with that tag.

- **Pushing a `v*` tag** deploys to staging; **Run workflow** (manual) deploys
  to staging or production. Staging uses the same production files on its own
  server with its own `.env`.
- Per environment (Settings, Environments), set the secrets `<ENV>_HOST`,
  `<ENV>_USER` and `<ENV>_SSH_KEY` (`<ENV>` is `STAGING` or `PRODUCTION`), the
  variable `STAGING_URL` or `PRODUCTION_URL` (e.g. `https://app.example.com`),
  and, for a server without a GPU, the variable `COMPOSE_EXTRA` set to
  `-f docker-compose.cpu.yml`.
- The server needs read access to the repository (for example a deploy key)
  for `git fetch`.

The workflow then checks `<URL>/health` for up to five minutes.

**Rollback:** on the server, set `IMAGE_TAG` to an earlier commit's short SHA
and run `pull` and `up -d` (section 5), or re-run an earlier workflow run.

## 9. Monitoring and logs

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f api-gateway celery-worker
```

- `https://app.example.com/health` for uptime monitoring (Uptime Kuma,
  Healthchecks.io, ...); `/health/ready` reports degraded dependencies,
  including a high share of template-fallback plans.
- Container logs rotate at 10 MB, five files per service.
- The API docs (`/docs`) are not routed through nginx, so they are not public.

## 10. Scaling

More API or worker processes on the same server:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale celery-worker=2
```

Plan generation is bound by the model: a second GPU (or a larger one) helps
more than extra workers. For high availability, move MongoDB to a replica set
or a managed service (MongoDB Atlas) and point the API at it.

## 11. Checklist

- [ ] GPU server (or `docker-compose.cpu.yml`), firewall open on 22/80/443 only
- [ ] `.env` with generated `JWT_SECRET` and `AES_KEY`, both saved in a password manager
- [ ] `DOMAIN`, `ALLOWED_ORIGINS` (JSON list), `FRONTEND_URL`, `MONGO_ROOT_*` set
- [ ] SMTP configured; password-reset email arrives
- [ ] TLS certificate issued; renewals switched to webroot; `certbot renew --dry-run` passes
- [ ] Model pulled; `/health/ready` shows `llm`, `ocr` and `mongodb` ok
- [ ] Admin account created by promotion (seed script **not** run)
- [ ] Daily MongoDB backups (uploads included), copied off the server
- [ ] Uptime monitoring on `/health`
- [ ] `/legal` reviewed by a lawyer, with a real contact address
