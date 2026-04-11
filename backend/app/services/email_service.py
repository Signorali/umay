"""
EmailService — async SMTP email sending (cloud.md §21).

Design rules:
  - If SMTP_ENABLED=False or SMTP not configured → silently returns False (no crash)
  - All sends are fire-and-forget safe (caller does not need to await completion)
  - Templates are simple plain-text + optional HTML
  - Never block the request thread; all I/O via aiosmtplib
  - This is infrastructure-only — business logic decides when to call this
"""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, List

from app.core.config import settings

logger = logging.getLogger("umay.email")


class EmailService:
    """Lightweight async email sender built on aiosmtplib."""

    async def send(
        self,
        to: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
    ) -> bool:
        """
        Send an email. Returns True on success, False if skipped or failed.
        Never raises — all failures are logged and swallowed.
        """
        if not settings.smtp_configured:
            logger.debug("[email] SMTP not configured — skipping '%s'", subject)
            return False

        try:
            import aiosmtplib  # lazy import — optional dependency
        except ImportError:
            logger.warning("[email] aiosmtplib not installed — cannot send email")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = ", ".join(to)
        if cc:
            msg["Cc"] = ", ".join(cc)

        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USERNAME,
                password=settings.SMTP_PASSWORD,
                use_tls=False,
                start_tls=settings.SMTP_TLS,
            )
            logger.info("[email] Sent '%s' → %s", subject, to)
            return True
        except Exception as exc:
            logger.error("[email] Failed to send '%s': %s", subject, exc)
            return False

    # ── Convenience templates ────────────────────────────────────────────────

    async def send_login_alert(self, to_email: str, ip_address: str) -> bool:
        """Security: notify user of new login."""
        return await self.send(
            to=[to_email],
            subject="Umay — Yeni Giriş Bildirimi",
            body_text=(
                f"Hesabınıza {ip_address} IP adresinden giriş yapıldı.\n"
                "Bu işlemi siz yapmadıysanız lütfen şifrenizi değiştirin."
            ),
            body_html=(
                f"<p>Hesabınıza <strong>{ip_address}</strong> IP adresinden giriş yapıldı.</p>"
                "<p>Bu işlemi siz yapmadıysanız lütfen şifrenizi değiştirin.</p>"
            ),
        )

    async def send_backup_done(self, to_email: str, filename: str, size_kb: int) -> bool:
        """Ops: notify admin when backup completes."""
        return await self.send(
            to=[to_email],
            subject="Umay — Yedekleme Tamamlandı",
            body_text=f"Yedekleme başarıyla tamamlandı.\nDosya: {filename}\nBoyut: {size_kb} KB",
        )

    async def send_backup_failed(self, to_email: str, error: str) -> bool:
        """Ops: notify admin when backup fails."""
        return await self.send(
            to=[to_email],
            subject="Umay — Yedekleme BAŞARISIZ ⚠️",
            body_text=f"Yedekleme başarısız oldu!\nHata: {error}",
        )

    async def send_license_expiry_warning(
        self, to_email: str, days_remaining: int
    ) -> bool:
        """License: notify admin before license expires."""
        return await self.send(
            to=[to_email],
            subject=f"Umay — Lisans {days_remaining} gün içinde bitiyor",
            body_text=(
                f"Umay lisansınızın sona ermesine {days_remaining} gün kaldı.\n"
                "Lisansınızı yenilemek için satıcınızla iletişime geçin."
            ),
        )

    async def send_payment_overdue(
        self, to_email: str, title: str, due_date: str, amount: float, currency: str
    ) -> bool:
        """Finance: notify user of overdue planned payment."""
        return await self.send(
            to=[to_email],
            subject=f"Umay — Gecikmiş Ödeme: {title}",
            body_text=(
                f"'{title}' ödemesi {due_date} tarihinde vadesini geçti.\n"
                f"Tutar: {amount:.2f} {currency}"
            ),
        )

    async def send_password_changed(self, to_email: str) -> bool:
        """Security: notify user their password was changed."""
        return await self.send(
            to=[to_email],
            subject="Umay — Şifreniz Değiştirildi",
            body_text=(
                "Hesabınızın şifresi başarıyla değiştirildi.\n"
                "Bu işlemi siz yapmadıysanız lütfen yöneticinize başvurun."
            ),
        )
