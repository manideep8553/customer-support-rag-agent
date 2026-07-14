import logging
from pathlib import Path
from typing import Optional

from backend.ports.document_loader import DocumentLoader, DocumentChunk
from backend.config import settings
from backend.errors import DocumentLoadError, log_exception

logger = logging.getLogger("gigacorp.chunking")


class LangChainMarkdownLoader(DocumentLoader):
    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self._text_splitter = None
        self._init_splitter()

    def _init_splitter(self) -> None:
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            self._text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
                length_function=len,
                keep_separator=True,
            )
        except ImportError:
            logger.warning("langchain_text_splitters not installed. Install with: pip install langchain-text-splitters")
            self._text_splitter = None
        except Exception as e:
            logger.error("Failed to initialize text splitter: %s", e)
            self._text_splitter = None

    def load(self, path: str) -> list[DocumentChunk]:
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"Knowledge base file not found: {path}")
        try:
            text = filepath.read_text(encoding="utf-8")
        except PermissionError as e:
            raise DocumentLoadError(f"Permission denied reading file: {path}", cause=e)
        except Exception as e:
            raise DocumentLoadError(f"Failed to read file: {path}", cause=e)
        source = filepath.name
        return self.chunk(text, source=source)

    def chunk(self, text: str, source: str = "knowledge_base") -> list[DocumentChunk]:
        try:
            if self._text_splitter:
                chunks = self._text_splitter.split_text(text)
            else:
                chunks = [text]
        except Exception as e:
            log_exception(e, "LangChainMarkdownLoader.chunk")
            raise DocumentLoadError("Failed to split text into chunks", cause=e)

        result = []
        for i, content in enumerate(chunks):
            content = content.strip()
            if not content:
                continue
            heading = ""
            for line in content.split("\n"):
                if line.startswith("##") or line.startswith("#"):
                    heading = line.strip("# ").strip()
                    break
            result.append(DocumentChunk(
                content=content,
                metadata={
                    "source": source,
                    "heading": heading,
                    "chunk_index": i,
                    "chunk_count": len(chunks),
                },
            ))
        return result
