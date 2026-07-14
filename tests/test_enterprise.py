import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_audit_logs_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/enterprise/audit-logs")
    # Should return 403 without auth
    assert response.status_code == 403 or response.status_code == 401


@pytest.mark.asyncio
async def test_rate_limits_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/enterprise/rate-limits")
    assert response.status_code == 401  # No auth


@pytest.mark.asyncio
async def test_enterprise_health_detailed(client: AsyncClient):
    response = await client.get("/api/v1/enterprise/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert "overall" in data
    assert "checks" in data


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    response = await client.get("/metrics")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_enterprise_metrics_json(client: AsyncClient):
    response = await client.get("/api/v1/enterprise/metrics")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_file_upload_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/enterprise/files/upload",
        files={"file": ("test.txt", b"hello world", "text/plain")},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_notifications_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/enterprise/notifications")
    assert response.status_code == 401  # No auth
