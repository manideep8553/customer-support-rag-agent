from typing import Protocol, Optional


class DocumentChunk:
    def __init__(self, content: str, metadata: dict | None = None):
        self.content = content
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        return {"content": self.content, "metadata": self.metadata}


class DocumentLoader(Protocol):
    def load(self, path: str) -> list[DocumentChunk]: ...

    def chunk(self, text: str, source: str = "knowledge_base") -> list[DocumentChunk]: ...
