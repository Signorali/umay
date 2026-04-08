"""
Background worker — ARQ-based async job queue.

Usage:
    arq app.worker.WorkerSettings

Jobs:
    - sync_calendar: Rebuild CalendarItems for a tenant
    - poll_market_prices: Fetch latest prices for watchlist symbols
    - process_ocr_draft: Run OCR extraction on a document
    - send_overdue_alerts: Mark overdue obligations and notify
    - create_backup: Create a full encrypted backup (cloud.md §8.15)
    - process_import: Process a large CSV import in the background (cloud.md §22)
    - generate_report: Generate a heavy report and store the result (cloud.md §8.12)

Cloud rules:
    - Each job must be idempotent (safe to retry)
    - Never auto-create confirmed transactions from jobs
    - Always log errors; never silently swallow exceptions
"""
import logging
import uuid
from datetime import timedelta
from typing import Any, Optional

from arq import create_pool, cron
from arq.connections import RedisSettings

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Redis connection for enqueueing ─────────────────────────────────────────

def get_arq_redis_settings() -> RedisSettings:
    """Parse REDIS_URL (redis://[:password@]host[:port][/db]) into RedisSettings."""
    from urllib.parse import urlparse
    url = urlparse(settings.REDIS_URL)
    return RedisSettings(
        host=url.hostname or "localhost",
        port=url.port or 6379,
        password=url.password or None,
        database=int(url.path.lstrip("/") or "0"),
    )


async def get_arq_pool():
    """Get ARQ Redis pool for enqueueing jobs from FastAPI."""
    return await create_pool(get_arq_redis_settings())


# ─── Job implementations ──────────────────────────────────────────────────────

async def sync_calendar(ctx: dict, tenant_id: str, user_id: str) -> dict:
    """
    Rebuild CalendarItems for a given user within a tenant.
    Sources: planned_payments, loan_installments, credit_card due dates.
    Returns count of items synced.
    """
    from app.core.database import AsyncSessionLocal
    from app.services.calendar_service import CalendarService

    logger.info("[arq:sync_calendar] tenant=%s user=%s", tenant_id, user_id)
    try:
        async with AsyncSessionLocal() as session:
            svc = CalendarService(session)
            count = await svc.sync_for_user(
                tenant_id=uuid.UUID(tenant_id),
                user_id=uuid.UUID(user_id),
            )
            await session.commit()
        logger.info("[arq:sync_calendar] synced %d items", count)
        return {"status": "ok", "items_synced": count}
    except Exception as exc:
        logger.exception("[arq:sync_calendar] failed: %s", exc)
        raise


async def poll_market_prices(ctx: dict) -> dict:
    """
    Fetch latest prices for all active watchlist symbols.
    Creates PriceSnapshot records — never modifies transactions.
    """
    from app.core.database import AsyncSessionLocal
    from app.services.market_service import MarketService

    logger.info("[arq:poll_market_prices] starting")
    try:
        async with AsyncSessionLocal() as session:
            svc = MarketService(session)
            result = await svc.refresh_all_prices()
            await session.commit()
        logger.info("[arq:poll_market_prices] updated %d symbols", result.get("updated", 0))
        return result
    except Exception as exc:
        logger.exception("[arq:poll_market_prices] failed: %s", exc)
        raise


async def process_ocr_draft(ctx: dict, draft_id: str) -> dict:
    """
    Run OCR extraction on an OcrDraft record.
    IMPORTANT: This only fills suggested_* fields — NEVER creates a real transaction.
    Status transitions: PENDING → PROCESSING → READY | FAILED
    """
    from app.core.database import AsyncSessionLocal
    from app.services.ocr_service import OcrService

    logger.info("[arq:process_ocr_draft] draft_id=%s", draft_id)
    try:
        async with AsyncSessionLocal() as session:
            svc = OcrService(session)
            result = await svc.process_draft(uuid.UUID(draft_id))
            await session.commit()
        return result
    except Exception as exc:
        logger.exception("[arq:process_ocr_draft] failed: %s", exc)
        raise


async def send_payment_due_alerts(ctx: dict) -> dict:
    """
    Send PAYMENT_DUE notifications for planned payments whose planned_date is today.
    Runs daily at 08:00. Group-based: each user only receives notifications
    for payments belonging to their group(s) — or all payments if no group.
    Uses idempotency_key to prevent duplicate notifications.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService
    from app.models.notification import NotificationType, NotificationPriority
    from app.models.planned_payment import PlannedPayment, PlannedPaymentStatus
    from app.models.user import User, UserGroup

    logger.info("[arq:send_payment_due_alerts] starting")
    total_notified = 0
    try:
        async with AsyncSessionLocal() as session:
            notif_svc = NotificationService(session)
            today = datetime.now(timezone.utc).date()

            result = await session.execute(
                select(PlannedPayment).where(
                    PlannedPayment.planned_date == today,
                    PlannedPayment.status == PlannedPaymentStatus.PENDING,
                    PlannedPayment.is_deleted == False,
                )
            )
            due_payments = result.scalars().all()

            for pp in due_payments:
                # Find users who can see this payment (group-based)
                if pp.group_id:
                    user_result = await session.execute(
                        select(User).join(UserGroup, UserGroup.user_id == User.id).where(
                            UserGroup.group_id == pp.group_id,
                            User.tenant_id == pp.tenant_id,
                            User.is_deleted == False,
                            User.is_active == True,
                        )
                    )
                else:
                    user_result = await session.execute(
                        select(User).where(
                            User.tenant_id == pp.tenant_id,
                            User.is_deleted == False,
                            User.is_active == True,
                        )
                    )
                users = user_result.scalars().all()

                for user in users:
                    ikey = f"payment_due:{pp.id}:{today}"
                    await notif_svc.create(
                        tenant_id=pp.tenant_id,
                        user_id=user.id,
                        notification_type=NotificationType.PAYMENT_DUE,
                        priority=NotificationPriority.MEDIUM,
                        title=f"Ödeme Günü: {pp.title}",
                        body=f"{float(pp.amount):,.2f} {pp.currency} tutarında ödemeniz bugün.",
                        action_url="/planned-payments",
                        meta={"pp_id": str(pp.id), "amount": str(pp.amount), "currency": pp.currency},
                        idempotency_key=ikey,
                    )
                    total_notified += 1

            await session.commit()
        logger.info("[arq:send_payment_due_alerts] notified=%d", total_notified)
        return {"status": "ok", "notifications_sent": total_notified}
    except Exception as exc:
        logger.exception("[arq:send_payment_due_alerts] failed: %s", exc)
        raise


async def send_overdue_alerts(ctx: dict) -> dict:
    """
    Mark overdue calendar items and planned payments.
    Creates PAYMENT_OVERDUE notifications for affected users.
    Does NOT create transactions — only updates status fields + sends notifications.
    """
    from app.core.database import AsyncSessionLocal
    from app.services.calendar_service import CalendarService
    from app.services.notification_service import NotificationService
    from app.models.notification import NotificationType, NotificationPriority

    logger.info("[arq:send_overdue_alerts] starting")
    total_notified = 0
    try:
        async with AsyncSessionLocal() as session:
            cal_svc = CalendarService(session)
            notif_svc = NotificationService(session)

            # Get overdue items before marking (returns list of dicts with user info)
            overdue_items = await cal_svc.get_overdue_items()

            # Notify each user about their overdue obligations
            for item in overdue_items:
                ikey = f"overdue:{item['id']}"
                await notif_svc.create(
                    tenant_id=uuid.UUID(item["tenant_id"]),
                    user_id=uuid.UUID(item["user_id"]),
                    notification_type=NotificationType.PAYMENT_OVERDUE,
                    priority=NotificationPriority.HIGH,
                    title=f"Gecikmiş Ödeme: {item['title']}",
                    body=f"Vadesi {item['due_date']} olan ödeme gerçekleştirilmedi.",
                    action_url="/calendar",
                    meta={"item_id": str(item["id"]), "due_date": str(item["due_date"])},
                    idempotency_key=ikey,
                )
                total_notified += 1

            # Mark them as overdue
            count = await cal_svc.mark_overdue_items()
            await session.commit()

        logger.info("[arq:send_overdue_alerts] marked=%d notified=%d", count, total_notified)
        return {"status": "ok", "overdue_marked": count, "notifications_sent": total_notified}
    except Exception as exc:
        logger.exception("[arq:send_overdue_alerts] failed: %s", exc)
        raise


async def create_backup(ctx: dict, label: Optional[str] = None) -> dict:
    """
    Create a full encrypted backup of the database.
    cloud.md §8.15: backup must be auditable, checksum-validated, optionally encrypted.
    On completion, sends email alert if SMTP is configured (cloud.md §21).
    """
    from app.services.backup_service import BackupService
    from app.services.email_service import EmailService
    from app.core.config import settings

    logger.info("[arq:create_backup] starting label=%s", label)
    email_svc = EmailService()

    try:
        svc = BackupService()
        result = await svc.create_backup(label=label)
        logger.info("[arq:create_backup] completed: %s", result)

        # Email notification on success (cloud.md §21)
        if settings.smtp_configured and settings.SMTP_USERNAME:
            await email_svc.send_backup_done(
                to_email=settings.SMTP_FROM_EMAIL,
                filename=result.get("filename", "?"),
                size_kb=result.get("size_bytes", 0) // 1024,
            )

        return result
    except Exception as exc:
        logger.exception("[arq:create_backup] failed: %s", exc)
        # Email failure alert
        if settings.smtp_configured:
            await email_svc.send_backup_failed(
                to_email=settings.SMTP_FROM_EMAIL,
                error=str(exc)[:200],
            )
        raise


async def process_import(
    ctx: dict,
    import_job_id: str,
    tenant_id: str,
    user_id: str,
) -> dict:
    """
    Process a large CSV import in the background.
    cloud.md §22: import must support validation report and partial failure reporting.
    IMPORTANT: Each row is validated before write. No half-written state on failure.
    """
    from app.core.database import AsyncSessionLocal
    from app.services.import_service import ImportService

    logger.info(
        "[arq:process_import] job_id=%s tenant=%s user=%s",
        import_job_id, tenant_id, user_id,
    )
    try:
        async with AsyncSessionLocal() as session:
            svc = ImportService(session)
            result = await svc.process_background_import(
                import_job_id=import_job_id,
                tenant_id=uuid.UUID(tenant_id),
                user_id=uuid.UUID(user_id),
            )
            await session.commit()
        logger.info(
            "[arq:process_import] done: imported=%d errors=%d",
            result.get("imported", 0), result.get("errors", 0),
        )
        return result
    except Exception as exc:
        logger.exception("[arq:process_import] failed: %s", exc)
        raise


async def generate_report(
    ctx: dict,
    report_type: str,
    tenant_id: str,
    user_id: str,
    params: Optional[dict] = None,
) -> dict:
    """
    Generate a heavy report and store the result for async retrieval.
    cloud.md §8.12: heavy report generation is worker-eligible.
    Reports are never blocking — UI polls for completion.
    """
    from app.core.database import AsyncSessionLocal
    from app.services.report_service import ReportService

    logger.info(
        "[arq:generate_report] type=%s tenant=%s user=%s",
        report_type, tenant_id, user_id,
    )
    try:
        async with AsyncSessionLocal() as session:
            svc = ReportService(session)
            result = await svc.generate_async(
                report_type=report_type,
                tenant_id=uuid.UUID(tenant_id),
                user_id=uuid.UUID(user_id),
                params=params or {},
            )
            await session.commit()
        logger.info("[arq:generate_report] completed type=%s", report_type)
        return result
    except Exception as exc:
        logger.exception("[arq:generate_report] failed: %s", exc)
        raise


async def sync_external_calendars(ctx: dict) -> dict:
    """
    Push Umay calendar items to all connected Google/Outlook accounts.
    Runs every 15 minutes. Safe to retry — events are upserted not duplicated.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.calendar_integration import CalendarIntegration
    from app.services.external_calendar_service import ExternalCalendarService
    from sqlalchemy import select

    logger.info("[arq:sync_external_calendars] starting")
    total = {}
    try:
        async with AsyncSessionLocal() as session:
            q = select(
                CalendarIntegration.user_id,
                CalendarIntegration.tenant_id,
            ).where(
                CalendarIntegration.is_active == True,
                CalendarIntegration.is_deleted == False,
            ).distinct()
            rows = list((await session.execute(q)).all())

        for row in rows:
            try:
                async with AsyncSessionLocal() as session:
                    svc = ExternalCalendarService(session)
                    result = await svc.sync_all_for_user(row.user_id, row.tenant_id)
                    total[str(row.user_id)] = result
            except Exception as e:
                logger.warning("[arq:sync_external_calendars] user=%s error: %s", row.user_id, e)

        logger.info("[arq:sync_external_calendars] done users=%d", len(rows))
        return {"status": "ok", "synced_users": len(rows), "results": total}
    except Exception as exc:
        logger.exception("[arq:sync_external_calendars] failed: %s", exc)
        raise


# ─── Startup / shutdown hooks ─────────────────────────────────────────────────

async def startup(ctx: dict) -> None:
    """Worker startup — initialize DB pool."""
    from app.core.database import engine
    logger.info("[arq:worker] starting up")
    ctx["engine"] = engine


async def shutdown(ctx: dict) -> None:
    """Worker shutdown — close connections."""
    logger.info("[arq:worker] shutting down")


# ─── WorkerSettings ───────────────────────────────────────────────────────────

class WorkerSettings:
    """
    ARQ WorkerSettings — run with:
        arq app.worker.WorkerSettings
    """
    functions = [
        sync_calendar,
        poll_market_prices,
        process_ocr_draft,
        send_payment_due_alerts,
        send_overdue_alerts,
        create_backup,
        process_import,
        generate_report,
        sync_external_calendars,
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = get_arq_redis_settings()

    # Cron schedules
    cron_jobs = [
        # Poll market prices every 15 minutes
        cron(
            coroutine=poll_market_prices,
            minute={0, 15, 30, 45},
            max_tries=3,
        ),
        # Send payment due notifications daily at 08:00
        cron(
            coroutine=send_payment_due_alerts,
            hour=8,
            minute=0,
            max_tries=2,
        ),
        # Mark overdue items every hour at :05
        cron(
            coroutine=send_overdue_alerts,
            minute=5,
            max_tries=2,
        ),
        # Sync Google/Outlook calendars every 15 minutes
        cron(
            coroutine=sync_external_calendars,
            minute={0, 15, 30, 45},
            max_tries=2,
        ),
    ]

    # Retry policy
    max_tries = 3
    job_timeout = 300  # 5 minutes max per job
    keep_result = 3600  # Keep results for 1 hour
