"""
CSRF Protection Middleware

Uses double-submit cookie pattern:
1. Server generates CSRF token on login, sets it in a non-httponly cookie
2. Client reads the cookie and sends the token in X-CSRF-Token header
3. Server verifies the header matches the cookie value

Exempt paths: login, register, health check, docs, static files
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/roles",
    "/api/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
}

EXEMPT_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/static",
    "/assets",
)

WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only check mutating requests
        if request.method not in WRITE_METHODS:
            return await call_next(request)

        # Skip exempt paths
        path = request.url.path
        if path in EXEMPT_PATHS or path.startswith(EXEMPT_PREFIXES):
            return await call_next(request)

        # Skip if no session cookie (unauthenticated requests)
        session_id = request.cookies.get("session_id")
        if not session_id:
            return await call_next(request)

        # Get CSRF token from cookie
        csrf_cookie = request.cookies.get("csrf_token")

        # Get CSRF token from header
        csrf_header = request.headers.get("x-csrf-token")

        # Verify tokens match
        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            return JSONResponse(
                status_code=403,
                content={"code": 403, "message": "CSRF token 验证失败", "data": None},
            )

        return await call_next(request)
