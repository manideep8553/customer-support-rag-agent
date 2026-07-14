from __future__ import annotations
from typing import Protocol, Optional, Any
from datetime import datetime


class DataRecord:
    def __init__(self, id: str, data: dict, created_at: datetime | None = None, updated_at: datetime | None = None):
        self.id = id
        self.data = data
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            **self.data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class StorageBackend(Protocol):
    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    async def create(self, collection: str, record: DataRecord) -> DataRecord: ...

    async def get(self, collection: str, id: str) -> Optional[DataRecord]: ...

    async def update(self, collection: str, id: str, data: dict) -> Optional[DataRecord]: ...

    async def delete(self, collection: str, id: str) -> bool: ...

    async def list(self, collection: str, limit: int = 100, offset: int = 0) -> list[DataRecord]: ...

    async def query(self, collection: str, filters: dict, limit: int = 100) -> list[DataRecord]: ...

    async def run_migrations(self) -> None: ...


class Migration(Protocol):
    @property
    def version(self) -> str: ...

    @property
    def description(self) -> str: ...

    async def up(self, backend: StorageBackend) -> None: ...

    async def down(self, backend: StorageBackend) -> None: ...
