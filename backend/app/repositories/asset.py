"""Asset and AssetValuation repositories."""
import uuid
from decimal import Decimal
from datetime import date
from typing import Optional, List
from sqlalchemy import select, update, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetValuation, AssetStatus, AssetLoanLink, AssetAccountLink


class AssetRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tenant_id: uuid.UUID, data: dict) -> Asset:
        obj = Asset(tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_by_id(self, asset_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Asset]:
        q = select(Asset).where(
            Asset.id == asset_id,
            Asset.tenant_id == tenant_id,
            Asset.is_deleted == False,
        )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        group_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        asset_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        group_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[Asset]:
        q = select(Asset).where(Asset.tenant_id == tenant_id, Asset.is_deleted == False)
        if group_ids:
            q = q.where(Asset.group_id.in_(group_ids))
        elif group_id:
            q = q.where(Asset.group_id == group_id)
        if status:
            q = q.where(Asset.status == status)
        if asset_type:
            q = q.where(Asset.asset_type == asset_type)
        q = q.order_by(Asset.name).offset(skip).limit(limit)
        return list((await self.db.execute(q)).scalars().all())

    async def update(self, asset: Asset, data: dict) -> Asset:
        for k, v in data.items():
            setattr(asset, k, v)
        await self.db.flush()
        await self.db.refresh(asset)
        return asset

    async def get_loan_ids(self, asset_id: uuid.UUID) -> List[uuid.UUID]:
        q = select(AssetLoanLink.loan_id).where(AssetLoanLink.asset_id == asset_id)
        return list((await self.db.execute(q)).scalars().all())

    async def get_account_ids(self, asset_id: uuid.UUID) -> List[uuid.UUID]:
        q = select(AssetAccountLink.account_id).where(AssetAccountLink.asset_id == asset_id)
        return list((await self.db.execute(q)).scalars().all())

    async def sync_loan_links(self, asset_id: uuid.UUID, loan_ids: List[uuid.UUID]) -> None:
        await self.db.execute(sa_delete(AssetLoanLink).where(AssetLoanLink.asset_id == asset_id))
        for loan_id in loan_ids:
            self.db.add(AssetLoanLink(asset_id=asset_id, loan_id=loan_id))
        await self.db.flush()

    async def sync_account_links(self, asset_id: uuid.UUID, account_ids: List[uuid.UUID]) -> None:
        await self.db.execute(sa_delete(AssetAccountLink).where(AssetAccountLink.asset_id == asset_id))
        for account_id in account_ids:
            self.db.add(AssetAccountLink(asset_id=asset_id, account_id=account_id, link_type="source"))
        await self.db.flush()

    async def soft_delete(self, asset: Asset) -> None:
        asset.is_deleted = True
        await self.db.flush()

    async def get_total_value(
        self, tenant_id: uuid.UUID, group_id: Optional[uuid.UUID] = None,
        group_ids: Optional[List[uuid.UUID]] = None,
    ) -> dict:
        """Return {currency: total_current_value} for active owned assets."""
        q = select(Asset.currency, func.sum(Asset.current_value)).where(
            Asset.tenant_id == tenant_id,
            Asset.status == AssetStatus.OWNED,
            Asset.is_deleted == False,
        )
        if group_ids:
            q = q.where(Asset.group_id.in_(group_ids))
        elif group_id:
            q = q.where(Asset.group_id == group_id)
        q = q.group_by(Asset.currency)
        rows = (await self.db.execute(q)).all()
        return {row[0]: row[1] for row in rows}


class AssetValuationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, asset_id: uuid.UUID, data: dict) -> AssetValuation:
        obj = AssetValuation(asset_id=asset_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def list_by_asset(self, asset_id: uuid.UUID) -> List[AssetValuation]:
        q = select(AssetValuation).where(
            AssetValuation.asset_id == asset_id,
            AssetValuation.is_deleted == False,
        ).order_by(AssetValuation.valuation_date.desc())
        return list((await self.db.execute(q)).scalars().all())

    async def latest(self, asset_id: uuid.UUID) -> Optional[AssetValuation]:
        q = select(AssetValuation).where(
            AssetValuation.asset_id == asset_id,
            AssetValuation.is_deleted == False,
        ).order_by(AssetValuation.valuation_date.desc()).limit(1)
        return (await self.db.execute(q)).scalar_one_or_none()
