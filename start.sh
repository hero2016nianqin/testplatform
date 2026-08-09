#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Starting Test Platform ==="

# Kill existing
kill $(lsof -t -i:8000) 2>/dev/null || true
kill $(lsof -t -i:5173) 2>/dev/null || true
sleep 1

# Backend
echo "[1/2] Starting backend (FastAPI) on :8000..."
cd "$ROOT/backend"
PYTHONPATH="$(pwd)" nohup python3 -c "
import uvicorn
from app import create_app
uvicorn.run(create_app(), host='0.0.0.0', port=8000, log_level='error')
" > /tmp/fastapi.log 2>&1 &
sleep 3

# Frontend
echo "[2/2] Starting frontend (Vite) on :5173..."
cd "$ROOT/frontend"
nohup npm run dev > /tmp/vite.log 2>&1 &
sleep 3

echo ""
echo "✅ Test Platform started!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   Health:   http://localhost:8000/api/v1/health"
