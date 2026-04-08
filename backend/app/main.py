from contextlib import asynccontextmanager
import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.redis_client import get_redis, close_redis
from app.core.exceptions import UmayException
from app.core.errors import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.core.middleware.idempotency import IdempotencyMiddleware
from app.core.middleware.maintenance import MaintenanceMiddleware
from app.core.rate_limit import limiter
from app.api.v1.router import router as api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    _log = logging.getLogger(__name__)

    await get_redis()

    # Auto-seed system permissions on every startup (idempotent)
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.permission_service import PermissionService
        async with AsyncSessionLocal() as session:
            svc = PermissionService(session)
            result = await svc.seed_system_permissions()
            await session.commit()
            if result["created"] > 0:
                _log.info("Permission seed: %d created, %d skipped", result["created"], result["skipped"])
    except Exception as e:
        _log.warning("Permission auto-seed failed: %s", e)

    try:
        from app.worker import get_arq_redis_settings
        from arq import create_pool
        app.state.arq = await create_pool(get_arq_redis_settings())
    except Exception as e:
        _log.warning("ARQ pool init failed (worker may be unavailable): %s", e)
        app.state.arq = None
    yield
    if getattr(app.state, "arq", None):
        await app.state.arq.aclose()
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ================================================================ #
# Middlewares — CORS must be first
# ================================================================ #

# GZip compression for responses > 1KB (huge bandwidth savings for mobile)
if settings.ENABLE_GZIP_COMPRESSION:
    app.add_middleware(GZipMiddleware, minimum_size=1024)

# Performance monitoring middleware
@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    """Track endpoint response times and log slow queries."""
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000  # ms

    # Add performance header
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

    # Log slow endpoints
    if process_time > settings.SLOW_QUERY_THRESHOLD_MS:
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Slow endpoint: {request.method} {request.url.path} "
            f"({process_time:.0f}ms)"
        )

    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(IdempotencyMiddleware, redis_url=settings.REDIS_URL)
app.add_middleware(MaintenanceMiddleware, redis_url=settings.REDIS_URL)

# ------------------------------------------------------------------ #
# Exception handlers
# ------------------------------------------------------------------ #

@app.exception_handler(UmayException)
async def umay_exception_handler(request: Request, exc: UmayException):
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# ------------------------------------------------------------------ #
# Routers
# ------------------------------------------------------------------ #

app.include_router(api_v1_router)


@app.get("/", include_in_schema=False)
async def root():
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running"}
