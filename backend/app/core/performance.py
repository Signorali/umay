"""
Performance optimization utilities:
- Connection pooling
- Query caching strategies
- Response compression
- Rate limiting configurations
"""
from functools import wraps
from typing import Callable, Any
import time
import logging
from decimal import Decimal
import json

logger = logging.getLogger(__name__)


# ── DATABASE CONNECTION POOLING ────────────────────────────────
SQLALCHEMY_ENGINE_KWARGS = {
    "pool_size": 20,              # 20 persistent connections
    "max_overflow": 40,           # 40 additional temp connections
    "pool_recycle": 3600,         # Recycle connections after 1 hour
    "pool_pre_ping": True,        # Test connection before use
    "echo": False,                # No SQL logging in production
    "echo_pool": False,           # No pool logging
}

# ── REDIS CACHING STRATEGIES ────────────────────────────────
CACHE_TTL = {
    # User & Auth
    "user_preferences": 3600,        # 1 hour
    "user_summary": 300,             # 5 minutes

    # Market data
    "market_prices": 60,             # 1 minute (real-time)
    "watchlist_prices": 30,          # 30 seconds
    "tefas_search": 3600,            # 1 hour (static)

    # Portfolio & Investments
    "portfolio_summary": 300,        # 5 minutes
    "portfolio_value": 60,           # 1 minute
    "position_pnl": 60,              # 1 minute

    # Reports
    "dashboard_summary": 300,        # 5 minutes
    "income_expense_report": 600,    # 10 minutes
    "category_breakdown": 600,       # 10 minutes

    # Calendar
    "upcoming_items": 300,           # 5 minutes

    # Settings
    "system_flags": 3600,            # 1 hour
    "oauth_config": 3600,            # 1 hour
}

# ── COMPRESSION SETTINGS ────────────────────────────────
COMPRESSION_CONFIG = {
    "min_size": 1024,                # Compress responses > 1KB
    "quality": 6,                    # gzip compression level (1-9)
}

# ── RATE LIMITING ────────────────────────────────────
RATE_LIMITS = {
    "default": "100/minute",         # 100 requests/minute
    "auth": "5/minute",              # Auth endpoints: 5/minute
    "search": "30/minute",           # Search endpoints: 30/minute
    "market": "60/minute",           # Market data: 60/minute
    "public": "1000/hour",           # Public endpoints: 1000/hour
}

# ── QUERY OPTIMIZATION DECORATOR ────────────────────────────────
def optimize_query(func: Callable) -> Callable:
    """Decorator to log slow queries and suggest optimizations."""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start

            # Log slow queries (> 1 second)
            if elapsed > 1.0:
                logger.warning(
                    f"Slow query: {func.__name__} took {elapsed:.2f}s. "
                    "Consider adding indexes or eager loading."
                )
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"Query failed: {func.__name__} ({elapsed:.2f}s): {str(e)}")
            raise

    return wrapper


# ── JSON SERIALIZATION OPTIMIZATION ────────────────────────────────
class OptimizedJSONEncoder(json.JSONEncoder):
    """Compact JSON encoding for mobile apps."""
    def encode(self, o):
        # Compact without spaces
        return super().encode(o).replace(": ", ":").replace(", ", ",")

    def default(self, o):
        if isinstance(o, Decimal):
            # Return string for large numbers, float for small
            f = float(o)
            if abs(f) > 1e7:
                return str(o)
            return round(f, 6)
        return super().default(o)


# ── PAGINATION OPTIMIZATION ────────────────────────────────────
class PaginationConfig:
    """Standard pagination for large datasets."""
    DEFAULT_LIMIT = 50
    MAX_LIMIT = 500

    @staticmethod
    def validate_limit(limit: int) -> int:
        """Ensure limit is within bounds."""
        return min(max(limit, 1), PaginationConfig.MAX_LIMIT)


# ── QUERY EAGER LOADING ────────────────────────────────────
# Recommended eager loading patterns to avoid N+1 queries

EAGER_LOADS = {
    "transactions_with_category": [
        "category",  # Category details
    ],
    "portfolio_with_positions": [
        "positions",  # All positions in portfolio
    ],
    "position_with_transactions": [
        "transactions",  # All transactions for position
    ],
    "accounts_with_transactions": [
        "transactions",  # Recent transactions
    ],
}


# ── BATCH OPERATIONS ────────────────────────────────────
async def batch_insert_transactions(db, transactions: list, batch_size: int = 1000):
    """Insert transactions in batches to avoid memory issues."""
    for i in range(0, len(transactions), batch_size):
        batch = transactions[i:i + batch_size]
        db.add_all(batch)
        await db.flush()
        logger.info(f"Inserted batch {i // batch_size + 1} ({len(batch)} rows)")
    await db.commit()


# ── RESPONSE OPTIMIZATION FOR MOBILE ────────────────────────────────
def mobile_response_schema(data: dict) -> dict:
    """Compress response for mobile bandwidth."""
    return {
        "d": data,  # "data" → "d"
        "t": int(time.time()),  # Include timestamp for cache busting
    }


# ── MONITORING & METRICS ────────────────────────────────────
class PerformanceMetrics:
    """Track API performance metrics."""

    @staticmethod
    def log_endpoint_timing(endpoint: str, duration: float, status: int):
        """Log endpoint performance."""
        if duration > 1.0:
            logger.warning(f"Slow endpoint: {endpoint} ({duration:.2f}s) - {status}")
        elif duration > 0.5:
            logger.info(f"Moderate: {endpoint} ({duration:.2f}s) - {status}")


# ── CACHE KEY BUILDERS ────────────────────────────────────
class CacheKeys:
    """Cache key patterns for consistency."""

    @staticmethod
    def user_summary(user_id: str) -> str:
        return f"user_summary:{user_id}"

    @staticmethod
    def portfolio_value(portfolio_id: str) -> str:
        return f"portfolio_value:{portfolio_id}"

    @staticmethod
    def market_price(symbol: str) -> str:
        return f"market_price:{symbol}"

    @staticmethod
    def watchlist(user_id: str) -> str:
        return f"watchlist:{user_id}"

    @staticmethod
    def dashboard(user_id: str) -> str:
        return f"dashboard:{user_id}"
