"""
Pagination helper — consistent cursor/offset pagination for all list endpoints.
"""
from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated list wrapper."""
    items: List[T]
    total: Optional[int] = None   # optional: expensive count query
    skip: int
    limit: int
    has_more: bool

    model_config = {"arbitrary_types_allowed": True}


def paginate(items: list, skip: int, limit: int, total: Optional[int] = None) -> dict:
    """Build a pagination response dict from a list slice."""
    has_more = len(items) == limit
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": has_more,
    }
