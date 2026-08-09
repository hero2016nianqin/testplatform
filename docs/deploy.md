# Deployment Guide

## Prerequisites

- Docker & Docker Compose v2
- Git

## Production Deployment

```bash
# Clone
git clone <repo-url> test-platform
cd test-platform/deploy

# Configure
cp .env.example .env
# Edit .env: set SECRET_KEY, DB_PASSWORD, MINIO keys, CORS_ORIGINS

# Deploy
bash scripts/deploy.sh
```

This will:
1. Pull Docker images
2. Build backend & frontend
3. Start: PostgreSQL, Redis, MinIO, FastAPI backend (uvicorn, 4 workers), Celery worker + beat, Nginx + Vue SPA
4. Initialize database (create tables + seed data)

## Services

| Service | Port | Description |
|---|---|---|
| Frontend | 80 | Nginx + Vue SPA |
| Backend API | internal | FastAPI on :8000 |
| PostgreSQL | internal | :5432 |
| Redis | internal | :6379 |
| MinIO | internal | :9000 (API), :9001 (Console) |

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | (required) | App secret key |
| `DB_PASSWORD` | (required) | PostgreSQL password |
| `CORS_ORIGINS` | `[]` | Allowed CORS origins |
| `MINIO_ACCESS_KEY` | `testplatform` | MinIO access key |
| `MINIO_SECRET_KEY` | `testplatform123` | MinIO secret key |
| `LOG_LEVEL` | `INFO` | Log level |

## Scaling

For higher concurrency:

```bash
# Increase backend workers
docker compose -f deploy/docker-compose.yml up -d --scale backend=3

# Increase celery workers
docker compose -f deploy/docker-compose.yml up -d --scale celery-worker=2
```

## Monitoring

- API: `http://<host>/api/v1/health`
- MinIO Console: `http://<host>:9001`
- Swagger UI (dev only): `http://<host>/api/docs`

## Backup

```bash
# Database
docker exec -t test-platform-postgres-1 pg_dump -U testplatform testplatform > backup.sql

# MinIO data
tar czf minio-backup.tar.gz /var/lib/docker/volumes/deploy_minio_data/
```
