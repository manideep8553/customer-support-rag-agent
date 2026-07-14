import logging
from typing import Optional

from backend.config import settings
from backend.enterprise.email_service.service import get_email_service
from backend.enterprise.notifications.models import Notification, NotificationChannel, NotificationPriority
from backend.enterprise.websocket.manager import get_ws_manager

logger = logging.getLogger("gigacorp.notifications")


class NotificationService:
    def __init__(self):
        self._enabled = settings.notification_enabled
        self._ws_manager = None
        self._email_service = None

    async def _get_ws(self):
        if self._ws_manager is None:
            self._ws_manager = await get_ws_manager()
        return self._ws_manager

    def _get_email(self):
        if self._email_service is None:
            self._email_service = get_email_service()
        return self._email_service

    async def send(
        self,
        user_id: str,
        title: str,
        body: str,
        channel: NotificationChannel = NotificationChannel.WEBSOCKET,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[dict] = None,
        category: str = "general",
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            channel=channel,
            priority=priority,
            title=title,
            body=body,
            data=data or {},
            category=category,
        )

        if channel in (NotificationChannel.WEBSOCKET, NotificationChannel.BOTH):
            try:
                ws = await self._get_ws()
                await ws.send_to_user(
                    user_id,
                    "notification",
                    notification.model_dump(),
                )
            except Exception as e:
                logger.warning("Failed to send WS notification to user %s: %s", user_id, e)

        if channel in (NotificationChannel.EMAIL, NotificationChannel.BOTH):
            try:
                email_service = self._get_email()
                if email_service.is_enabled():
                    await email_service.send_notification_email(
                        user_id=user_id,
                        subject=title,
                        body=body,
                        notification_data=data,
                    )
            except Exception as e:
                logger.warning("Failed to send email notification to user %s: %s", user_id, e)

        logger.debug("Notification sent to user %s: %s", user_id, title)
        return notification

    async def notify_ticket_assigned(self, user_id: str, ticket_number: str, assigned_by: str):
        await self.send(
            user_id=user_id,
            title="Ticket Assigned",
            body=f"Ticket {ticket_number} has been assigned to you by {assigned_by}.",
            priority=NotificationPriority.HIGH,
            category="ticket",
            data={"ticket_number": ticket_number, "action": "assigned"},
        )

    async def notify_ticket_escalated(self, user_id: str, ticket_number: str, reason: str):
        await self.send(
            user_id=user_id,
            title="Ticket Escalated",
            body=f"Ticket {ticket_number} has been escalated: {reason}",
            priority=NotificationPriority.URGENT,
            category="ticket",
            data={"ticket_number": ticket_number, "action": "escalated"},
        )

    async def notify_ticket_resolved(self, user_id: str, ticket_number: str):
        await self.send(
            user_id=user_id,
            title="Ticket Resolved",
            body=f"Your ticket {ticket_number} has been resolved.",
            priority=NotificationPriority.NORMAL,
            category="ticket",
            data={"ticket_number": ticket_number, "action": "resolved"},
        )

    async def notify_order_update(self, user_id: str, order_number: str, status: str):
        await self.send(
            user_id=user_id,
            title="Order Update",
            body=f"Order {order_number} status updated to: {status}",
            priority=NotificationPriority.NORMAL,
            category="order",
            data={"order_number": order_number, "status": status},
        )

    async def notify_shipment_update(self, user_id: str, tracking_number: str, status: str):
        await self.send(
            user_id=user_id,
            title="Shipment Update",
            body=f"Shipment {tracking_number} is now: {status}",
            priority=NotificationPriority.NORMAL,
            category="shipment",
            data={"tracking_number": tracking_number, "status": status},
        )


_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
