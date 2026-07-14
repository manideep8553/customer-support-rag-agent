import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from backend.auth.database import Base


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    SUPPORT_AGENT = "support_agent"
    ADMIN = "admin"
    PREMIUM = "premium"
    SUPPORT = "support"
    USER = "user"


class Permission(str, enum.Enum):
    READ_TICKETS = "read:tickets"
    WRITE_TICKETS = "write:tickets"
    MANAGE_TICKETS = "manage:tickets"
    READ_ORDERS = "read:orders"
    WRITE_ORDERS = "write:orders"
    MANAGE_SHIPMENTS = "manage:shipments"
    READ_USERS = "read:users"
    MANAGE_USERS = "manage:users"
    READ_AUDIT_LOGS = "read:audit_logs"
    MANAGE_KNOWLEDGE_BASE = "manage:knowledge_base"
    VIEW_ANALYTICS = "view:analytics"
    MANAGE_SETTINGS = "manage:settings"
    SEND_NOTIFICATIONS = "send:notifications"
    READ_CONVERSATIONS = "read:conversations"
    CHAT = "chat"


ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.CUSTOMER: {
        Permission.CHAT,
        Permission.READ_TICKETS,
        Permission.WRITE_TICKETS,
        Permission.READ_ORDERS,
    },
    UserRole.PREMIUM: {
        Permission.CHAT,
        Permission.READ_TICKETS,
        Permission.WRITE_TICKETS,
        Permission.READ_ORDERS,
        Permission.WRITE_ORDERS,
    },
    UserRole.SUPPORT: {
        Permission.CHAT,
        Permission.READ_TICKETS,
        Permission.WRITE_TICKETS,
        Permission.MANAGE_TICKETS,
        Permission.READ_ORDERS,
        Permission.WRITE_ORDERS,
        Permission.MANAGE_SHIPMENTS,
        Permission.READ_CONVERSATIONS,
    },
    UserRole.SUPPORT_AGENT: {
        Permission.CHAT,
        Permission.READ_TICKETS,
        Permission.WRITE_TICKETS,
        Permission.MANAGE_TICKETS,
        Permission.READ_ORDERS,
        Permission.WRITE_ORDERS,
        Permission.MANAGE_SHIPMENTS,
        Permission.READ_CONVERSATIONS,
        Permission.VIEW_ANALYTICS,
    },
    UserRole.ADMIN: {
        Permission.CHAT,
        Permission.READ_TICKETS,
        Permission.WRITE_TICKETS,
        Permission.MANAGE_TICKETS,
        Permission.READ_ORDERS,
        Permission.WRITE_ORDERS,
        Permission.MANAGE_SHIPMENTS,
        Permission.READ_USERS,
        Permission.MANAGE_USERS,
        Permission.READ_AUDIT_LOGS,
        Permission.MANAGE_KNOWLEDGE_BASE,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_SETTINGS,
        Permission.SEND_NOTIFICATIONS,
        Permission.READ_CONVERSATIONS,
    },
    UserRole.USER: {
        Permission.CHAT,
        Permission.READ_TICKETS,
        Permission.WRITE_TICKETS,
        Permission.READ_ORDERS,
    },
}


def _utcnow():
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(200), nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.CUSTOMER, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    avatar_url = Column(String(500), nullable=True)
    company = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    preferences = Column(Text, nullable=True)
    department = Column(String(100), nullable=True)
    job_title = Column(String(200), nullable=True)

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)

    password_reset_token = Column(String(500), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    email_verification_token = Column(String(500), nullable=True)

    @property
    def permissions(self) -> set[Permission]:
        return ROLE_PERMISSIONS.get(self.role, set())

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions or self.role == UserRole.ADMIN

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "display_name": self.display_name,
            "role": self.role.value if self.role else "customer",
            "permissions": [p.value for p in self.permissions],
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "avatar_url": self.avatar_url,
            "company": self.company,
            "phone": self.phone,
            "department": self.department,
            "job_title": self.job_title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(50), nullable=True)
