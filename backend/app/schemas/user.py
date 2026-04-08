import uuid
from typing import List, Optional, Set
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role_id: Optional[uuid.UUID] = None
    is_tenant_admin: bool = False
    locale: Optional[str] = None
    timezone: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    is_tenant_admin: Optional[bool] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    is_tenant_admin: bool
    role_id: Optional[uuid.UUID]
    last_login_at: Optional[datetime]
    locale: Optional[str]
    timezone: Optional[str]
    ui_theme: Optional[str]
    must_change_password: bool = False
    permissions: List[str] = []   # ['transactions:view', ...] or ['*'] for admins
    created_at: datetime

    model_config = {"from_attributes": True}
