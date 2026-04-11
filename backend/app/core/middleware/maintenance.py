"""
Maintenance mode middleware.

If maintenance_mode flag is 'true', returns HTTP 503 for all endpoints
except: /api/v1/health, /api/v1/system/maintenance (to allow re-enabling)
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

BYPASS_PATHS = {
    "/api/v1/health",
    "/api/v1/system/maintenance",
    "/api/v1/system/flags",
    "/",
}


class MaintenanceMiddleware(BaseHTTPMiddleware):
    """
    Checks Redis or DB for maintenance_mode flag on each request.
    Uses Redis as fast-path to avoid DB hit on every request.
    """

    def __init__(self, app: ASGIApp, redis_url: str = "redis://localhost:6379/0"):
        super().__init__(app)
        self.redis_url = redis_url
        self._redis = None

    async def _is_maintenance(self) -> bool:
        try:
            import redis.asyncio as aioredis
            if self._redis is None:
                self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
            val = await self._redis.get("umay:maintenance_mode")
            return val == "true"
        except Exception:
            return False  # fail-open: never block if Redis is down

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in BYPASS_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        if await self._is_maintenance():
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "code": "SERVICE_UNAVAILABLE",
                        "message": "System is currently under maintenance. Please try again shortly.",
                    }
                },
                headers={"Retry-After": "300"},
            )

        return await call_next(request)
