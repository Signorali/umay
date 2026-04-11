"""AssetService — asset lifecycle, valuation, and disposal management."""
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.asset import AssetRepository, AssetValuationRepository
from app.services.audit_service import AuditService
from app.models.asset import AssetStatus, AssetLoanLink, AssetAccountLink
from app.schemas.transaction import TransactionCreate, TransactionType


class AssetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AssetRepository(db)
        self.valuation_repo = AssetValuationRepository(db)
        self.audit = AuditService(db)

    async def _attach_links(self, asset) -> None:
        """Attach loan_ids and source_account_ids as instance attributes for response serialization."""
        asset.loan_ids = await self.repo.get_loan_ids(asset.id)
        asset.source_account_ids = await self.repo.get_account_ids(asset.id)

    async def _attach_links_bulk(self, assets: list) -> None:
        """Bulk-load links for a list of assets (2 queries total)."""
        if not assets:
            return
        from sqlalchemy import select
        asset_ids = [a.id for a in assets]
        loan_rows = list((await self.db.execute(
            select(AssetLoanLink.asset_id, AssetLoanLink.loan_id)
            .where(AssetLoanLink.asset_id.in_(asset_ids))
        )).all())
        acc_rows = list((await self.db.execute(
            select(AssetAccountLink.asset_id, AssetAccountLink.account_id)
            .where(AssetAccountLink.asset_id.in_(asset_ids))
        )).all())
        loan_map: dict = {}
        for r in loan_rows:
            loan_map.setdefault(r.asset_id, []).append(r.loan_id)
        acc_map: dict = {}
        for r in acc_rows:
            acc_map.setdefault(r.asset_id, []).append(r.account_id)
        for asset in assets:
            asset.loan_ids = loan_map.get(asset.id, [])
            asset.source_account_ids = acc_map.get(asset.id, [])

    async def create_asset(
        self, tenant_id: uuid.UUID, actor_id: uuid.UUID, data: dict
    ):
        loan_ids: list = data.pop("loan_ids", []) or []
        source_account_ids: list = data.pop("source_account_ids", []) or []
        # Legacy single-value fields — merge into lists if lists are empty
        legacy_loan_id = data.pop("loan_id", None)
        legacy_source = data.pop("source_account_id", None)
        legacy_account = data.pop("account_id", None)
        if not loan_ids and legacy_loan_id:
            loan_ids = [legacy_loan_id]
        if not source_account_ids and legacy_source:
            source_account_ids = [legacy_source]

        # Strip junction-only fields from Asset model kwargs
        clean_data = {k: v for k, v in data.items() if k not in ("loan_ids", "source_account_ids")}
        asset = await self.repo.create(tenant_id, clean_data)

        # Record opening valuation
        await self.valuation_repo.create(asset.id, {
            "valuation_date": asset.purchase_date,
            "value": asset.purchase_value,
            "currency": asset.currency,
            "source": "purchase",
        })

        # Sync junction tables
        await self.repo.sync_loan_links(asset.id, [uuid.UUID(str(i)) for i in loan_ids])
        await self.repo.sync_account_links(asset.id, [uuid.UUID(str(i)) for i in source_account_ids])

        # Deduct from first source account (purchase transaction)
        if source_account_ids:
            from app.services.transaction_service import TransactionService
            tx_svc = TransactionService(self.db)
            await tx_svc.create(
                tenant_id=tenant_id,
                group_id=None,
                data=TransactionCreate(
                    transaction_type=TransactionType.EXPENSE,
                    source_account_id=source_account_ids[0],
                    amount=asset.purchase_value,
                    currency=asset.currency,
                    transaction_date=asset.purchase_date,
                    description=f"Varlık alımı: {asset.name}",
                    system_generated=True,
                ),
                actor_id=actor_id,
            )
        await self.audit.log(
            actor_id=actor_id, action="asset.create",
            module="assets", record_id=asset.id,
            new_state={"name": asset.name, "purchase_value": str(asset.purchase_value)},
        )
        await self.db.commit()
        await self.db.refresh(asset)
        await self._attach_links(asset)
        return asset

    async def update_asset(
        self, asset_id: uuid.UUID, tenant_id: uuid.UUID,
        actor_id: uuid.UUID, data: dict
    ):
        loan_ids = data.pop("loan_ids", None)
        source_account_ids = data.pop("source_account_ids", None)

        asset = await self._get_or_404(asset_id, tenant_id)
        old = {"name": asset.name, "current_value": str(asset.current_value)}
        updated = await self.repo.update(asset, data)

        if loan_ids is not None:
            await self.repo.sync_loan_links(asset_id, [uuid.UUID(str(i)) for i in loan_ids])
        if source_account_ids is not None:
            await self.repo.sync_account_links(asset_id, [uuid.UUID(str(i)) for i in source_account_ids])

        await self.audit.log(
            actor_id=actor_id, action="asset.update",
            module="assets", record_id=asset_id,
            old_state=old, new_state={"current_value": str(updated.current_value)},
        )
        await self.db.commit()
        await self.db.refresh(updated)
        await self._attach_links(updated)
        return updated

    async def add_valuation(
        self, asset_id: uuid.UUID, tenant_id: uuid.UUID,
        actor_id: uuid.UUID, valuation_data: dict
    ):
        asset = await self._get_or_404(asset_id, tenant_id)
        valuation = await self.valuation_repo.create(asset.id, valuation_data)

        # Update asset's current_value if newer
        if not asset.valuation_date or valuation_data["valuation_date"] >= asset.valuation_date:
            await self.repo.update(asset, {
                "current_value": valuation_data["value"],
                "valuation_date": valuation_data["valuation_date"],
            })

        await self.audit.log(
            actor_id=actor_id, action="asset.valuation_added",
            module="assets", record_id=asset_id,
            new_state={"value": str(valuation_data["value"])},
        )
        await self.db.commit()
        await self.db.refresh(valuation)
        return valuation

    async def dispose_asset(
        self, asset_id: uuid.UUID, tenant_id: uuid.UUID,
        actor_id: uuid.UUID, sale_date: date,
        sale_value: Optional[Decimal], sale_notes: Optional[str],
        is_sold: bool = True,
        target_account_id: Optional[uuid.UUID] = None,
    ):
        asset = await self._get_or_404(asset_id, tenant_id)
        if asset.status != AssetStatus.OWNED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Asset is already {asset.status} and cannot be disposed again.",
            )

        new_status = AssetStatus.SOLD if is_sold else AssetStatus.DISPOSED
        update_data = {
            "status": new_status,
            "sale_date": sale_date,
            "sale_value": sale_value,
            "sale_notes": sale_notes,
        }
        if sale_value is not None:
            update_data["current_value"] = sale_value

        updated = await self.repo.update(asset, update_data)
        gain = (sale_value - asset.purchase_value) if sale_value else None

        # Credit sale proceeds to target account if provided
        if target_account_id and sale_value:
            from app.services.transaction_service import TransactionService
            tx_svc = TransactionService(self.db)
            sale_tx = await tx_svc.create(
                tenant_id=tenant_id,
                group_id=None,
                data=TransactionCreate(
                    transaction_type=TransactionType.INCOME,
                    target_account_id=target_account_id,
                    amount=sale_value,
                    currency=asset.currency,
                    transaction_date=sale_date,
                    description=f"Varlık satışı: {asset.name}",
                    system_generated=True,
                ),
                actor_id=actor_id,
            )
            # Link transaction to asset so deletion can revert status
            await self.repo.update(updated, {"sale_transaction_id": sale_tx.id})

        await self.audit.log(
            actor_id=actor_id, action="asset.dispose",
            module="assets", record_id=asset_id,
            new_state={
                "status": new_status.value,
                "sale_value": str(sale_value) if sale_value else None,
                "gain_loss": str(gain) if gain else None,
            },
        )
        await self.db.commit()
        await self.db.refresh(updated)
        await self._attach_links(updated)
        return updated

    async def get_portfolio_summary(
        self, tenant_id: uuid.UUID, group_id: Optional[uuid.UUID] = None,
        group_ids: Optional[List[uuid.UUID]] = None,
    ) -> dict:
        total_by_currency = await self.repo.get_total_value(tenant_id, group_id, group_ids=group_ids)
        assets = await self.repo.list_by_tenant(
            tenant_id, group_id=group_id, status="OWNED", limit=1000,
            group_ids=group_ids if group_ids is not None else [],
        )
        purchase_total: dict = {}
        for a in assets:
            purchase_total[a.currency] = purchase_total.get(a.currency, Decimal("0")) + a.purchase_value

        result = {}
        for currency, current in total_by_currency.items():
            purchase = purchase_total.get(currency, Decimal("0"))
            result[currency] = {
                "current_value": float(current),
                "purchase_value": float(purchase),
                "unrealized_gain": float(current - purchase),
            }
        return result

    async def list_assets(
        self, tenant_id: uuid.UUID, group_id=None,
        status=None, asset_type=None, skip=0, limit=50,
        group_ids: Optional[List[uuid.UUID]] = None,
    ):
        assets = await self.repo.list_by_tenant(
            tenant_id, group_id=group_id,
            status=status, asset_type=asset_type,
            skip=skip, limit=limit, group_ids=group_ids or [],
        )
        await self._attach_links_bulk(assets)
        return assets

    async def get_asset(self, asset_id: uuid.UUID, tenant_id: uuid.UUID):
        asset = await self._get_or_404(asset_id, tenant_id)
        await self._attach_links(asset)
        return asset

    async def get_valuations(self, asset_id: uuid.UUID, tenant_id: uuid.UUID):
        await self._get_or_404(asset_id, tenant_id)
        return await self.valuation_repo.list_by_asset(asset_id)

    async def delete_asset(
        self, asset_id: uuid.UUID, tenant_id: uuid.UUID, actor_id: uuid.UUID
    ):
        asset = await self._get_or_404(asset_id, tenant_id)
        if asset.status == AssetStatus.OWNED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete an active asset. Dispose it first.",
            )
        await self.repo.soft_delete(asset)
        await self.audit.log(
            actor_id=actor_id, action="asset.delete",
            module="assets", record_id=asset_id,
        )
        await self.db.commit()

    async def _get_or_404(self, asset_id: uuid.UUID, tenant_id: uuid.UUID):
        asset = await self.repo.get_by_id(asset_id, tenant_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        return asset
