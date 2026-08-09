from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.ws.manager import get_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    manager = get_manager()
    await manager.start_redis_listener()

    yield

    await manager.stop_redis_listener()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Test Platform API",
        version="2.0.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    from app.routers import register_routers
    register_routers(app)

    return app
