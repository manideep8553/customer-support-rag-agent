import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from backend.config import settings

logger = logging.getLogger("gigacorp.email")


class EmailService:
    def __init__(self):
        self._enabled = settings.email_enabled
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._user = settings.smtp_user
        self._password = settings.smtp_password
        self._use_tls = settings.smtp_use_tls
        self._from_name = settings.email_from_name
        self._from_address = settings.email_from_address

    def is_enabled(self) -> bool:
        return self._enabled and bool(self._host)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        if not self.is_enabled():
            logger.warning("Email not sent: email service disabled. Would send to %s: %s", to_email, subject)
            return False

        try:
            import aiosmtplib

            message = MIMEMultipart("alternative")
            message["From"] = f"{self._from_name} <{self._from_address}>"
            message["To"] = to_email
            message["Subject"] = subject

            if text_body:
                message.attach(MIMEText(text_body, "plain"))
            message.attach(MIMEText(html_body, "html"))

            await aiosmtplib.send(
                message,
                hostname=self._host,
                port=self._port,
                username=self._user,
                password=self._password,
                use_tls=self._use_tls,
            )
            logger.info("Email sent to %s: %s", to_email, subject)
            return True
        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, e)
            return False

    async def send_notification_email(
        self,
        user_id: str,
        subject: str,
        body: str,
        notification_data: Optional[dict] = None,
    ) -> bool:
        import uuid as _uuid

        from sqlalchemy import select

        from backend.auth.database import async_session_factory
        from backend.auth.models import User

        try:
            async with async_session_factory() as db:
                result = await db.execute(select(User).where(User.id == _uuid.UUID(user_id)))
                user = result.scalar_one_or_none()
                if not user:
                    logger.warning("User %s not found for email notification", user_id)
                    return False

                html_body = f"""<html><body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #2563eb;">{subject}</h2>
                <p>{body}</p>
                <hr>
                <p style="color: #666; font-size: 12px;">GigaCorp Customer Support</p>
                </body></html>"""

                return await self.send_email(
                    to_email=user.email,
                    subject=subject,
                    html_body=html_body,
                    text_body=body,
                )
        except Exception as e:
            logger.error("Failed to send notification email for user %s: %s", user_id, e)
            return False


_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
