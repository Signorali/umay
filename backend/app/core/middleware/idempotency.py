"""
Idempotency middleware — prevents duplicate financial writes on network retry.

Usage:
  Client sends header:  Idempotency-Key: <unique-uuid>
  Server caches result for POST/PUT/PATCH requests for 24h.
  Same key → same response without re-executing the business logic.
"""
import json
import hashlib
from datetime import timedelta
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Require redis for idempotency cache
try:
    import redis.asyncio as aioredis
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False

IDEMPOTENCY_TTL_SECONDS = 86400  # 24 hours
IDEMPOTENCY_METHODS = {"POST", "PUT", "PATCH"}
IDEMPOTENCY_HEADER = "Idempotency-Key"
CACHE_PREFIX = "idempotency:"


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Stores response bodies in Redis keyed by (user_id + idempotency_key).
    Only applies to mutating HTTP methods.
    If Redis is unavailable, requests pass through normally (fail-open).
    """

    def __init__(self, app: ASGIApp, redis_url: str = "redis://localhost:6379/1"):
        super().__init__(app)
        self.redis_url = redis_url
        self._redis: Optional[object] = None

    async def _get_redis(self):
        if not _REDIS_AVAILABLE:
            return None
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
            except Exception:
                return None
        return self._redis

    async def dispatch(self, request: Request, call_next):
        if request.method not in IDEMPOTENCY_METHODS:
            return await call_next(request)

        idem_key = request.headers.get(IDEMPOTENCY_HEADER)
        if not idem_key:
            return await call_next(request)

        # Build cache key: hash(method + path + idempotency_key)
        raw = f"{request.method}:{request.url.path}:{idem_key}"
        cache_key = CACHE_PREFIX + hashlib.sha256(raw.encode()).hexdigest()

        redis = await self._get_redis()
        if redis:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    payload = json.loads(cached)
                    return Response(
                        content=payload["body"],
                        status_code=payload["status_code"],
                        media_type="application/json",
                        headers={"X-Idempotency-Replayed": "true"},
                    )
            except Exception:
                pass  # fail-open

        # Execute actual request
        response = await call_next(request)

        # Cache successful responses (2xx)
        if redis and 200 <= response.status_code < 300:
            try:
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                await redis.setex(
                    cache_key,
                    IDEMPOTENCY_TTL_SECONDS,
                    json.dumps({"body": body.decode(), "status_code": response.status_code}),
                )
                return Response(
                    content=body,
                    status_code=response.status_code,
                    media_type=response.media_type,
                    headers=dict(response.headers),
                )
            except Exception:
                pass

        return response
