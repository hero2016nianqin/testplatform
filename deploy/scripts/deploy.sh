#!/bin/bash
# Test Platform — Production Deployment Script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.yml"
ENV_FILE="$DEPLOY_DIR/.env"

echo "=== Test Platform Deployment ==="

# Check env file
if [ ! -f "$ENV_FILE" ]; then
    echo "[!] .env file not found at $ENV_FILE"
    echo "    Copy from .env.example and edit:"
    echo "    cp $DEPLOY_DIR/.env.example $ENV_FILE"
    exit 1
fi

# Pull latest images
echo "[1/4] Pulling Docker images..."
docker compose -f "$COMPOSE_FILE" pull

# Build and start services
echo "[2/4] Building and starting services..."
docker compose -f "$COMPOSE_FILE" up -d --build

# Wait for health checks
echo "[3/4] Waiting for services to be healthy..."
sleep 10

# Run database initialization (seed data)
echo "[4/4] Initializing database..."
docker compose -f "$COMPOSE_FILE" exec -T backend python -c "
import asyncio
from app.core.database import engine, Base
from scripts.seed_data import seed

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed()
    print('Database initialized successfully')

asyncio.run(init())
"

echo "=== Deployment complete ==="
echo "Frontend: http://localhost"
echo "API:      http://localhost/api/v1/health"
echo "MinIO:    http://localhost/minio"
