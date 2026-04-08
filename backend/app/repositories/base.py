import uuid
from typing import Any, Generic, List, Optional, Type, TypeVar
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """Generic async repository. No SQL in service or route layer."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, record_id: uuid.UUID) -> Optional[ModelType]:
        result = await self.session.get(self.model, record_id)
        if result and not result.is_deleted:
            return result
        return None

    async def list_all(
        self,
        filters: Optional[List[Any]] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[List[ModelType], int]:
        query = select(self.model).where(self.model.is_deleted == False)
        if filters:
            query = query.where(*filters)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar_one()

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: ModelType, **kwargs: Any) -> ModelType:
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def soft_delete(self, obj: ModelType) -> None:
        obj.is_deleted = True
        await self.session.flush()
