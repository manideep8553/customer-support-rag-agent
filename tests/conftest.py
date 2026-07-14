import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings

settings.database_url = "sqlite+aiosqlite:///./test.db"
settings.cache_enabled = False
settings.rate_limiting_enabled = False
settings.audit_enabled = False
settings.notification_enabled = False
settings.email_enabled = False


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def app():
    from backend.main import app
    return app


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    from backend.auth.database import async_session_factory, init_db, close_db
    await init_db()
    async with async_session_factory() as session:
        yield session
        await session.rollback()
    await close_db()


@pytest.fixture
def auth_headers():
    return {"X-API-Key": ""}


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "TestPass123",
            "display_name": "Test User",
        },
    )
    return response.json()
