import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from backend.core.pipeline import Pipeline
from backend.config import settings
from backend.errors import DocumentLoadError

logger = logging.getLogger("gigacorp.ingestion")


@dataclass
class Document:
    content: str
    metadata: dict = field(default_factory=dict)
    source: str = ""
    path: str | None = None


DocumentProcessor = Callable[[Document, dict], Document]


def default_processors() -> list[tuple[str, DocumentProcessor]]:
    from backend.ingestion.processors.text import TextNormalizer, TextChunker, MetadataEnricher
    from backend.ingestion.processors.sanitizer import ContentSanitizer

    return [
        ("normalize", TextNormalizer()),
        ("sanitize", ContentSanitizer()),
        ("enrich_metadata", MetadataEnricher()),
        ("chunk", TextChunker(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)),
    ]


class DocumentPipeline:
    def __init__(self):
        self.pipeline = Pipeline[Document]("document_ingestion")
        for name, processor in default_processors():
            self.pipeline.add(name, processor)

    def add_processor(self, name: str, processor: DocumentProcessor, after: str | None = None) -> "DocumentPipeline":
        if after:
            self.pipeline.insert_after(after, name, processor)
        else:
            self.pipeline.add(name, processor)
        return self

    def remove_processor(self, name: str) -> "DocumentPipeline":
        self.pipeline.remove(name)
        return self

    def process(self, doc: Document) -> list[Document]:
        result = self.pipeline.run(doc)
        return result if isinstance(result, list) else [result]

    def process_text(self, text: str, source: str = "inline", metadata: dict | None = None) -> list[Document]:
        doc = Document(content=text, source=source, metadata=metadata or {})
        return self.process(doc)

    def process_file(self, file_path: str) -> list[Document]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        text = path.read_text(encoding="utf-8")
        metadata = {"filename": path.name, "path": str(path), "size": path.stat().st_size}
        return self.process_text(text, source=path.name, metadata=metadata)


pipeline = DocumentPipeline()
