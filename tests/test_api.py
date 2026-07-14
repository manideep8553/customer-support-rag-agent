import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_endpoint(client: AsyncClient, registered_user):
    token = registered_user["access_token"]
    session_id = registered_user["user"]["id"]

    response = await client.post(
        "/api/v1/chat",
        json={
            "session_id": session_id,
            "message": "Hello, how are you?",
        },
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "session_id" in data


@pytest.mark.asyncio
async def test_chat_empty_message(client: AsyncClient, registered_user):
    token = registered_user["access_token"]
    response = await client.post(
        "/api/v1/chat",
        json={"session_id": "test", "message": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient, registered_user):
    token = registered_user["access_token"]
    response = await client.post(
        "/api/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201 or response.status_code == 200
    data = response.json()
    assert "session_id" in data or "id" in str(data)


@pytest.mark.asyncio
async def test_list_sessions(client: AsyncClient, registered_user):
    token = registered_user["access_token"]
    response = await client.get(
        "/api/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_cache_stats(client: AsyncClient):
    response = await client.get("/api/v1/cache/stats")
    assert response.status_code == 200
    data = response.json()
    assert "embedding_cache" in data
