"""Dashboard widget Pydantic schemas."""
import uuid
from typing import Optional, Any
from pydantic import BaseModel


class DashboardWidgetUpdate(BaseModel):
    title: Optional[str] = None
    position: Optional[int] = None
    col_span: Optional[int] = None
    row_span: Optional[int] = None
    config: Optional[dict] = None
    is_visible: Optional[bool] = None


class DashboardWidgetResponse(BaseModel):
    id: uuid.UUID
    widget_type: str
    title: Optional[str]
    position: int
    col_span: int
    row_span: int
    config: Optional[dict]
    is_visible: bool

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    user_id: str
    tenant_id: str
    period: dict
    widgets: list
