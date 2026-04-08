"""
Rate Limiting — slowapi integration for Umay.

Usage in endpoints:
    from app.core.rate_limit import limiter

    @router.post("/login")
    @limiter.limit("5/minute")
    async def login(request: Request, ...):
        ...

The limiter uses the client IP address by default.
For auth endpoints, this provides brute-force protection (cloud.md §14).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Global limiter instance — import this in endpoints
limiter = Limiter(key_func=get_remote_address)


def get_limiter() -> Limiter:
    """Dependency accessor for the global limiter."""
    return limiter
