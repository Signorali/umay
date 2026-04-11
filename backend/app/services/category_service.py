"""Category service."""
import uuid
from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category, CategoryType
from app.repositories.category import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.audit_service import AuditService
from app.core.exceptions import NotFoundError, ConflictError, BusinessRuleError


class CategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CategoryRepository(session)
        self.audit = AuditService(session)

    async def create(
        self,
        tenant_id: uuid.UUID,
        data: CategoryCreate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Category:
        # Validate parent if provided
        if data.parent_id:
            parent = await self.repo.get_by_id_and_tenant(data.parent_id, tenant_id)
            if not parent:
                raise NotFoundError("Parent category")
            if parent.category_type != data.category_type:
                raise BusinessRuleError(
                    "Category type must match parent category type"
                )

        if await self.repo.name_exists(data.name, tenant_id, data.parent_id):
            raise ConflictError(f"Category '{data.name}' already exists at this level")

        category = Category(
            tenant_id=tenant_id,
            group_id=data.group_id,
            parent_id=data.parent_id,
            name=data.name,
            category_type=data.category_type,
            description=data.description,
            icon=data.icon,
            color=data.color,
        )
        category = await self.repo.create(category)
        await self.audit.log(
            action="CREATE",
            module="categories",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(category.id),
            after={"name": category.name, "type": category.category_type},
        )
        return category

    async def get_by_id(self, category_id: uuid.UUID, tenant_id: uuid.UUID) -> Category:
        category = await self.repo.get_by_id_and_tenant(category_id, tenant_id)
        if not category:
            raise NotFoundError("Category")
        return category

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, offset: int = 0, limit: int = 100,
        group_ids: Optional[List[uuid.UUID]] = None,
    ) -> Tuple[List[Category], int]:
        return await self.repo.get_by_tenant(tenant_id, offset=offset, limit=limit, group_ids=group_ids)

    async def list_by_type(
        self, category_type: CategoryType, tenant_id: uuid.UUID
    ) -> List[Category]:
        return await self.repo.get_by_type(category_type, tenant_id)

    async def update(
        self,
        category_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: CategoryUpdate,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> Category:
        category = await self.get_by_id(category_id, tenant_id)
        if category.is_system:
            raise BusinessRuleError("Sistem kategorileri değiştirilemez")

        before = {
            "name": category.name,
            "description": category.description,
            "icon": category.icon,
            "color": category.color,
            "is_active": category.is_active
        }
        update_fields = data.model_dump(exclude_unset=True)
        category = await self.repo.update(category, **update_fields)
        
        await self.audit.log(
            action="UPDATE",
            module="categories",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(category_id),
            before=before,
            after=update_fields,
        )
        return category

    async def delete(
        self,
        category_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        actor_email: Optional[str] = None,
    ) -> None:
        category = await self.get_by_id(category_id, tenant_id)
        if category.is_system:
            raise BusinessRuleError("System categories cannot be deleted")

        children = await self.repo.get_children(category_id)
        if children:
            raise BusinessRuleError(
                "Bu kategorinin alt kategorileri var. Önce onları silmelisiniz."
            )

        # Check for transactions
        from app.models.transaction import Transaction
        tx_count = await self.session.scalar(
            select(func.count(Transaction.id)).where(
                Transaction.category_id == category_id,
                Transaction.is_deleted == False
            )
        )
        if tx_count and tx_count > 0:
            raise BusinessRuleError(
                "Bu kategoriye ait işlemler bulunduğu için silinemez."
            )

        await self.repo.soft_delete(category)
        await self.audit.log(
            action="DELETE",
            module="categories",
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            record_id=str(category_id),
        )
