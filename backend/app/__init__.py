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

    # ── HTTPS enforcement (production only, behind reverse proxy) ──
    if not settings.DEBUG:
        from starlette.middleware.base import BaseHTTPMiddleware

        class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                forwarded_proto = request.headers.get("x-forwarded-proto")
                if forwarded_proto and forwarded_proto != "https":
                    from starlette.responses import RedirectResponse
                    url = request.url.replace(scheme="https")
                    return RedirectResponse(url, status_code=301)
                return await call_next(request)

        app.add_middleware(HTTPSRedirectMiddleware)

    # ── CSRF protection ──
    from app.core.csrf import CSRFMiddleware
    app.add_middleware(CSRFMiddleware)

    # ── Security headers ──
    from app.core.security_headers import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)

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
