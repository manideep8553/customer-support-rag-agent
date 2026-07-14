from typing import Protocol

from backend.ports.vector_store import SearchResult


class Reranker(Protocol):
    def rerank(self, query: str, results: list[SearchResult], top_k: int = 4) -> list[SearchResult]: ...

    @property
    def name(self) -> str: ...
