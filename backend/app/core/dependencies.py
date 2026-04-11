"""
app.core.dependencies — shim module.

All Phase 3-5 endpoints import from here.
This re-exports everything from app.api.deps so the actual
logic stays in one place.
"""
from app.api.deps import (
    get_current_user,
    get_current_superuser,
    get_current_tenant_admin,
    get_client_ip,
    require_permission,
    get_user_group_ids,
)

__all__ = [
    "get_current_user",
    "get_current_superuser",
    "get_current_tenant_admin",
    "get_client_ip",
    "require_permission",
    "get_user_group_ids",
]
