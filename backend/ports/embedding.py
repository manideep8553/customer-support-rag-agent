from typing import Protocol


class EmbeddingModel(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    @property
    def dimension(self) -> int: ...
