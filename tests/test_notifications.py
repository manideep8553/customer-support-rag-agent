import pytest
from backend.enterprise.notifications.service import NotificationService
from backend.enterprise.notifications.models import NotificationChannel, NotificationPriority


@pytest.mark.asyncio
async def test_notification_service_create():
    service = NotificationService()
    notification = await service.send(
        user_id="test-user",
        title="Test Notification",
        body="This is a test",
        channel=NotificationChannel.WEBSOCKET,
        priority=NotificationPriority.NORMAL,
        category="test",
    )
    assert notification.user_id == "test-user"
    assert notification.title == "Test Notification"
    assert notification.channel == NotificationChannel.WEBSOCKET


@pytest.mark.asyncio
async def test_notification_ticket_assigned():
    service = NotificationService()
    notification = await service.notify_ticket_assigned(
        user_id="agent-1",
        ticket_number="TKT-001",
        assigned_by="admin",
    )
    assert notification is not None
    assert "TKT-001" in notification.body
