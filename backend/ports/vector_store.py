from typing import Protocol, Optional
from dataclasses import dataclass


@dataclass
class SearchResult:
    content: str
    score: float
    source: str
    metadata: dict


class VectorStore(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def add(self, texts: list[str], metadata: Optional[list[dict]] = None) -> None: ...

    def search(self, query: str, k: Optional[int] = None, score_threshold: Optional[float] = None) -> list[SearchResult]: ...

    def delete(self) -> None: ...

    @property
    def is_initialized(self) -> bool: ...
