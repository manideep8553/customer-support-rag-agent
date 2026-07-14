import enum
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    WEBSOCKET = "websocket"
    BOTH = "both"


class NotificationPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    channel: NotificationChannel = NotificationChannel.WEBSOCKET
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str
    body: str
    data: Optional[dict] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    read: bool = False
    category: str = "general"
