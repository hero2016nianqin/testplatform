# Test Platform v2

生产测试管理平台 — FastAPI + Vue3 SPA 重构版。

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Celery |
| Frontend | Vue 3.4, TypeScript, Element Plus, Pinia, ECharts, Tailwind |
| Database | PostgreSQL 15 (monthly partitioning for test_runs/results/logs) |
| Cache | Redis 7 |
| Storage | MinIO (binary files) |
| Task | Celery (async test execution, log archiving, cleanup) |
| Schedule | XXL-Job (optional) |
| Deployment | Docker + Docker Compose + Nginx |

## Quick Start

### Development

```bash
# Backend
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app:create_app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Production

```bash
cd deploy
cp .env.example .env
# Edit .env with production secrets
bash scripts/deploy.sh
```

## Project Structure

```
├── backend/              # Python FastAPI backend
│   ├── app/
│   │   ├── config/       # Settings + constants
│   │   ├── core/         # DB, Redis, MinIO, security, exceptions
│   │   ├── models/       # SQLAlchemy ORM (26 tables)
│   │   ├── schemas/      # Pydantic request/response
│   │   ├── routers/      # FastAPI routes (7 modules)
│   │   ├── services/     # Business logic (6 services)
│   │   ├── deps/         # FastAPI Depends
│   │   ├── utils/        # Cache, pagination, export
│   │   └── ws/           # WebSocket manager
│   ├── tasks/            # Celery tasks
│   ├── scripts/          # Seed data, migrations
│   └── tests/            # pytest integration tests
├── frontend/             # Vue3 SPA
│   ├── src/
│   │   ├── api/          # Axios API wrappers
│   │   ├── stores/       # Pinia stores
│   │   ├── composables/  # Vue composables
│   │   ├── components/   # Shared components
│   │   ├── views/        # Page views (10 pages)
│   │   └── router/       # Vue Router
│   └── Dockerfile
├── deploy/               # Production deployment
│   ├── docker-compose.yml
│   ├── nginx.conf
│   ├── pg_init.sql
│   └── scripts/deploy.sh
└── docs/
    └── architecture-v2.md
```

## Key Features

- **Four-level RBAC**: operator(0) < process(1) < developer(2) < super_admin(3)
- **Equipment hierarchy**: Factory → ProductionLine → TestStation → Cabinet → Chassis → Slot
- **Test execution**: Barcode scan-to-test, traditional mode & sequence mode, real-time WebSocket logs
- **Version management**: Draft → Released → Deployed → Delisted lifecycle, two-stage approval
- **Async tasks**: Celery workers for long-running test execution, log compression, data cleanup
- **Partitioning**: `test_runs`, `test_results`, `test_logs` use monthly declarative partitioning
- **26 database tables**: Full coverage of original Flask SQLite model

## API Documentation

Once running, visit `/api/docs` (dev) for Swagger UI.

## License

Internal use only.
