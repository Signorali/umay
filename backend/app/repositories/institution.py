"""Institution, CommissionRule, and TaxRule repositories."""
import uuid
from typing import Optional, List
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import Institution, CommissionRule, TaxRule, InstitutionGroupLink


class InstitutionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: uuid.UUID, data: dict) -> Institution:
        obj = Institution(tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_by_id(self, institution_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Institution]:
        q = select(Institution).where(
            Institution.id == institution_id,
            Institution.tenant_id == tenant_id,
            Institution.is_deleted == False,
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        institution_type: Optional[str] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
        group_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[Institution]:
        q = select(Institution).where(Institution.tenant_id == tenant_id, Institution.is_deleted == False)
        if institution_type:
            q = q.where(Institution.institution_type == institution_type)
        if active_only:
            q = q.where(Institution.is_active == True)
        if group_ids:
            # Show institutions linked to any of the user's groups OR with no group links
            linked_ids_sub = (
                select(InstitutionGroupLink.institution_id)
                .where(InstitutionGroupLink.group_id.in_(group_ids))
            )
            no_link_sub = (
                select(InstitutionGroupLink.institution_id)
            )
            from sqlalchemy import not_, exists
            q = q.where(
                Institution.id.in_(linked_ids_sub) |
                ~Institution.id.in_(no_link_sub)
            )
        q = q.order_by(Institution.name).offset(skip).limit(limit)
        return list((await self.db.execute(q)).scalars().all())

    async def get_group_ids(self, institution_id: uuid.UUID) -> List[uuid.UUID]:
        q = select(InstitutionGroupLink.group_id).where(
            InstitutionGroupLink.institution_id == institution_id
        )
        return list((await self.db.execute(q)).scalars().all())

    async def sync_group_links(self, institution_id: uuid.UUID, group_ids: List[uuid.UUID]) -> None:
        await self.db.execute(
            sa_delete(InstitutionGroupLink).where(InstitutionGroupLink.institution_id == institution_id)
        )
        for gid in group_ids:
            self.db.add(InstitutionGroupLink(institution_id=institution_id, group_id=gid))
        await self.db.flush()

    async def get_group_ids_bulk(self, institution_ids: List[uuid.UUID]) -> dict:
        """Return {institution_id: [group_id, ...]} for bulk attachment."""
        if not institution_ids:
            return {}
        q = select(InstitutionGroupLink.institution_id, InstitutionGroupLink.group_id).where(
            InstitutionGroupLink.institution_id.in_(institution_ids)
        )
        rows = list((await self.db.execute(q)).all())
        result: dict = {}
        for r in rows:
            result.setdefault(r.institution_id, []).append(r.group_id)
        return result

    async def update(self, institution: Institution, data: dict) -> Institution:
        for k, v in data.items():
            setattr(institution, k, v)
        await self.db.flush()
        await self.db.refresh(institution)
        return institution

    async def soft_delete(self, institution: Institution) -> None:
        institution.is_deleted = True
        await self.db.flush()


class CommissionRuleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, institution_id: uuid.UUID, data: dict) -> CommissionRule:
        obj = CommissionRule(institution_id=institution_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def list_by_institution(self, institution_id: uuid.UUID) -> List[CommissionRule]:
        q = select(CommissionRule).where(
            CommissionRule.institution_id == institution_id,
            CommissionRule.is_deleted == False,
        ).order_by(CommissionRule.instrument_type)
        return list((await self.db.execute(q)).scalars().all())

    async def delete(self, rule: CommissionRule) -> None:
        rule.is_deleted = True
        await self.db.flush()


class TaxRuleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, institution_id: uuid.UUID, data: dict) -> TaxRule:
        obj = TaxRule(institution_id=institution_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def list_by_institution(self, institution_id: uuid.UUID) -> List[TaxRule]:
        q = select(TaxRule).where(
            TaxRule.institution_id == institution_id,
            TaxRule.is_deleted == False,
        ).order_by(TaxRule.rule_type)
        return list((await self.db.execute(q)).scalars().all())

    async def delete(self, rule: TaxRule) -> None:
        rule.is_deleted = True
        await self.db.flush()
