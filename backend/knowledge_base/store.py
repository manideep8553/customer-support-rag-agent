import logging
from pathlib import Path
from typing import Optional

from backend.config import settings
from backend.errors import (
    DocumentLoadError,
    EmbeddingError,
    VectorStoreError,
    log_exception,
)
from backend.ports.document_loader import DocumentLoader
from backend.ports.vector_store import VectorStore

logger = logging.getLogger("gigacorp.knowledge_base")


class KnowledgeBaseManager:
    def __init__(self, vector_store: VectorStore, doc_loader: DocumentLoader):
        self.vector_store = vector_store
        self.loader = doc_loader

    def ingest_file(self, file_path: Optional[str] = None) -> dict:
        if file_path:
            path = file_path
        else:
            kb_path = settings.knowledge_base_path
            md_files = list(kb_path.glob("*.md"))
            if not md_files:
                raise FileNotFoundError(f"No markdown files found in {kb_path}")
            path = str(md_files[0])

        try:
            chunks = self.loader.load(path)
        except DocumentLoadError:
            raise
        except Exception as e:
            log_exception(e, "KnowledgeBaseManager.ingest_file.load")
            raise DocumentLoadError(f"Failed to load file: {path}", cause=e)

        if not chunks:
            return {"status": "error", "chunks_ingested": 0, "message": "No chunks extracted from the file"}

        texts = [c.content for c in chunks]
        metadata = [c.metadata for c in chunks]
        source_name = Path(path).name

        for m in metadata:
            m["source"] = source_name

        try:
            self.vector_store.add(texts, metadata)
        except (VectorStoreError, EmbeddingError):
            raise
        except Exception as e:
            log_exception(e, "KnowledgeBaseManager.ingest_file.add")
            raise VectorStoreError("Failed to add chunks to vector store", cause=e)

        return {
            "status": "success",
            "chunks_ingested": len(chunks),
            "message": f"Successfully ingested {len(chunks)} chunks from {source_name}",
        }

    def ingest_text(self, text: str, source_name: str = "inline_text") -> dict:
        try:
            chunks = self.loader.chunk(text, source=source_name)
        except DocumentLoadError:
            raise
        except Exception as e:
            log_exception(e, "KnowledgeBaseManager.ingest_text.chunk")
            raise DocumentLoadError("Failed to chunk provided text", cause=e)

        if not chunks:
            return {"status": "error", "chunks_ingested": 0, "message": "No chunks extracted from the provided text"}

        texts = [c.content for c in chunks]
        metadata = [c.metadata for c in chunks]

        try:
            self.vector_store.add(texts, metadata)
        except (VectorStoreError, EmbeddingError):
            raise
        except Exception as e:
            log_exception(e, "KnowledgeBaseManager.ingest_text.add")
            raise VectorStoreError("Failed to add text chunks to vector store", cause=e)

        return {
            "status": "success",
            "chunks_ingested": len(chunks),
            "message": f"Successfully ingested {len(chunks)} chunks",
        }

    def status(self) -> dict:
        initialized = False
        chunk_count = 0
        try:
            initialized = self.vector_store.is_initialized
        except Exception as e:
            logger.warning("Failed to check vector store initialization: %s", e)
        try:
            if hasattr(self.vector_store, "chunk_count"):
                chunk_count = self.vector_store.chunk_count
            elif hasattr(self.vector_store, "_chunks") and self.vector_store._chunks:
                chunk_count = len(self.vector_store._chunks)
        except Exception as e:
            logger.warning("Failed to get chunk count: %s", e)
        return {
            "initialized": initialized,
            "chunk_count": chunk_count,
            "vector_store_path": str(settings.vector_store_path),
        }

    def ingest_all(self) -> dict:
        kb_path = settings.knowledge_base_path
        md_files = sorted(kb_path.glob("*.md"))
        if not md_files:
            raise FileNotFoundError(f"No markdown files found in {kb_path}")

        total_chunks = 0
        files_processed = 0
        file_errors = []

        for md_file in md_files:
            path = str(md_file)
            try:
                chunks = self.loader.load(path)
            except Exception as e:
                msg = f"Skipped {md_file.name}: {e}"
                logger.warning(msg)
                file_errors.append(msg)
                continue

            if not chunks:
                logger.warning("No chunks extracted from %s, skipping", md_file.name)
                continue

            texts = [c.content for c in chunks]
            metadata = [c.metadata for c in chunks]
            source_name = md_file.name
            for m in metadata:
                m["source"] = source_name

            try:
                self.vector_store.add(texts, metadata)
            except Exception as e:
                msg = f"Failed to add chunks from {md_file.name}: {e}"
                logger.error(msg)
                file_errors.append(msg)
                continue

            total_chunks += len(chunks)
            files_processed += 1

        message = f"Ingested {total_chunks} chunks from {files_processed} file(s)"
        if file_errors:
            message += f" with {len(file_errors)} error(s)"
            for err in file_errors:
                logger.info("  - %s", err)

        return {
            "status": "success" if files_processed > 0 else "error",
            "total_chunks": total_chunks,
            "files_processed": files_processed,
            "file_errors": file_errors,
            "message": message,
        }

    def rebuild(self) -> dict:
        old_count = 0
        try:
            old_count = self.status().get("chunk_count", 0)
            self.vector_store.delete()
        except Exception as e:
            logger.warning("Error during vector store clear: %s", e)

        result = self.ingest_all()
        result["old_chunks_cleared"] = old_count
        return result

    def clear(self):
        try:
            self.vector_store.delete()
        except Exception as e:
            log_exception(e, "KnowledgeBaseManager.clear")
            raise VectorStoreError("Failed to clear vector store", cause=e)
