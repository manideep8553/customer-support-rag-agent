import pytest
from backend.enterprise.email_service.service import EmailService


@pytest.mark.asyncio
async def test_email_service_disabled():
    service = EmailService()
    assert service.is_enabled() is False


@pytest.mark.asyncio
async def test_email_service_send_disabled():
    service = EmailService()
    result = await service.send_email(
        to_email="test@example.com",
        subject="Test",
        html_body="<p>Test</p>",
    )
    assert result is False


@pytest.mark.asyncio
async def test_email_notification_user_not_found():
    service = EmailService()
    result = await service.send_notification_email(
        user_id="nonexistent-user-id",
        subject="Test",
        body="Test body",
    )
    assert result is False
