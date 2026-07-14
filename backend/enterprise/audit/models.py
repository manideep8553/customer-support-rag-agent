import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Enum as SAEnum, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID

from backend.auth.database import Base


class AuditAction(str, enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    ESCALATE = "escalate"
    ASSIGN = "assign"
    RESOLVE = "resolve"
    CLOSE = "close"
    REOPEN = "reopen"
    API_CALL = "api_call"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True)
    actor_role = Column(String(50), nullable=True)
    action = Column(SAEnum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    outcome = Column(String(20), nullable=False, default="success")
    error_message = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)
    request_body_preview = Column(String(10000), nullable=True)
    response_status = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
