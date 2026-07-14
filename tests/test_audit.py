import pytest

from backend.config import settings
from backend.enterprise.audit.models import AuditAction
from backend.enterprise.audit.service import AuditService


@pytest.mark.asyncio
async def test_audit_service_log(db_session):
    original = settings.audit_enabled
    settings.audit_enabled = True
    service = AuditService()
    entry_id = await service.log(
        action=AuditAction.LOGIN,
        resource_type="user",
        resource_id="test-user-123",
        actor_id="00000000-0000-0000-0000-000000000001",
        actor_email="test@example.com",
        outcome="success",
    )
    assert entry_id is not None
    assert isinstance(entry_id, str)
    settings.audit_enabled = original


@pytest.mark.asyncio
async def test_audit_query(db_session):
    original = settings.audit_enabled
    settings.audit_enabled = True
    service = AuditService()
    await service.log(
        action=AuditAction.API_CALL,
        resource_type="api",
        resource_id="/api/v1/test",
        actor_id="00000000-0000-0000-0000-000000000002",
        outcome="success",
    )
    entries, total = await service.query(db=db_session, limit=10)
    assert total >= 1
    assert any(e["resource_type"] == "api" for e in entries)
    settings.audit_enabled = original


@pytest.mark.asyncio
async def test_audit_disabled():
    import backend.config
    original = backend.config.settings.audit_enabled
    backend.config.settings.audit_enabled = False

    service = AuditService()
    entry_id = await service.log(
        action=AuditAction.API_CALL,
        resource_type="test",
    )
    assert entry_id is None

    backend.config.settings.audit_enabled = original
