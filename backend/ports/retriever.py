from typing import Protocol

from backend.ports.vector_store import SearchResult


class Retriever(Protocol):
    def retrieve(self, query: str, k: int = 4, score_threshold: float | None = None) -> list[SearchResult]: ...

    @property
    def name(self) -> str: ...
