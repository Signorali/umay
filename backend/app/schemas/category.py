"""Category schemas."""
import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.models.category import CategoryType


def _to_title_case(text: str) -> str:
    """Convert text to Title Case."""
    if not text:
        return text
    return ' '.join(word.capitalize() for word in text.split())


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category_type: CategoryType
    parent_id: Optional[uuid.UUID] = None
    group_id: uuid.UUID = Field(...)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None

    @field_validator('name', mode='before')
    @classmethod
    def title_case_name(cls, v):
        if isinstance(v, str):
            return _to_title_case(v)
        return v


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator('name', mode='before')
    @classmethod
    def title_case_name(cls, v):
        if isinstance(v, str):
            return _to_title_case(v)
        return v


class CategoryResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    group_id: Optional[uuid.UUID]
    parent_id: Optional[uuid.UUID]
    name: str
    category_type: CategoryType
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    is_system: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryListResponse(BaseModel):
    items: list[CategoryResponse]
    total: int
