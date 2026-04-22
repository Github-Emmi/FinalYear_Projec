"""Async email service using aiosmtplib.

All methods silently no-op when SMTP_USER is not configured, so the app runs
without an SMTP server in development and tests.
"""

from __future__ import annotations

from email.message import EmailMessage

from app.core.config import get_settings


class EmailService:
    """Send transactional emails via async SMTP."""

    def __init__(self) -> None:
        self._settings = get_settings()

    async def send_email(self, to: str, subject: str, body: str) -> None:
        """Send a plain-text email.

        Silently returns when SMTP_USER is not configured.
        Errors are propagated to the caller (let upper layers decide retry logic).
        """
        settings = self._settings
        if not settings.SMTP_USER:
            return  # SMTP not configured — skip silently in dev/test

        import aiosmtplib  # lazy import: not all deployments need this at startup

        message = EmailMessage()
        message["From"] = settings.SMTP_FROM
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=settings.SMTP_TLS,
        )

    async def send_welcome(self, email: str, first_name: str) -> None:
        await self.send_email(
            to=email,
            subject="Welcome to School Management System",
            body=(
                f"Hi {first_name},\n\n"
                "Your account has been created successfully.\n\n"
                "Regards,\nSchool Admin"
            ),
        )

    async def send_leave_decision(
        self, email: str, first_name: str, status: str
    ) -> None:
        await self.send_email(
            to=email,
            subject=f"Leave Request {status.title()}",
            body=(
                f"Hi {first_name},\n\n"
                f"Your leave request has been {status}.\n\n"
                "Regards,\nSchool Admin"
            ),
        )

    async def send_password_reset(self, email: str, first_name: str, token: str) -> None:
        await self.send_email(
            to=email,
            subject="Password Reset Request",
            body=(
                f"Hi {first_name},\n\n"
                f"Use this token to reset your password: {token}\n\n"
                "This token expires in 30 minutes.\n\n"
                "If you did not request this, ignore this email.\n\n"
                "Regards,\nSchool Admin"
            ),
        )
