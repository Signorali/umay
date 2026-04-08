import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_validator


def _to_title_case(text: str) -> str:
    """Convert text to Title Case."""
    if not text:
        return text
    return ' '.join(word.capitalize() for word in text.split())


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None

    @field_validator('name', mode='before')
    @classmethod
    def title_case_name(cls, v):
        if isinstance(v, str):
            return _to_title_case(v)
        return v


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator('name', mode='before')
    @classmethod
    def title_case_name(cls, v):
        if isinstance(v, str):
            return _to_title_case(v)
        return v


class RoleResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: Optional[str]
    is_system: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PermissionCreate(BaseModel):
    module: str
    action: str
    description: Optional[str] = None


class PermissionResponse(BaseModel):
    id: uuid.UUID
    module: str
    action: str
    description: Optional[str]

    model_config = {"from_attributes": True}


class AssignPermissionRequest(BaseModel):
    permission_id: uuid.UUID
