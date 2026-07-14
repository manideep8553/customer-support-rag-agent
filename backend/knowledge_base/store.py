from pathlib import Path
from typing import Optional

from backend.config import settings
from backend.ports.vector_store import VectorStore
from backend.ports.document_loader import DocumentLoader


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

        chunks = self.loader.load(path)
        if not chunks:
            return {"status": "error", "chunks_ingested": 0, "message": "No chunks extracted"}

        texts = [c.content for c in chunks]
        metadata = [c.metadata for c in chunks]
        source_name = Path(path).name

        for m in metadata:
            m["source"] = source_name

        self.vector_store.add(texts, metadata)

        return {
            "status": "success",
            "chunks_ingested": len(chunks),
            "message": f"Successfully ingested {len(chunks)} chunks from {source_name}",
        }

    def ingest_text(self, text: str, source_name: str = "inline_text") -> dict:
        chunks = self.loader.chunk(text, source=source_name)
        if not chunks:
            return {"status": "error", "chunks_ingested": 0, "message": "No chunks extracted"}
        texts = [c.content for c in chunks]
        metadata = [c.metadata for c in chunks]
        self.vector_store.add(texts, metadata)
        return {
            "status": "success",
            "chunks_ingested": len(chunks),
            "message": f"Successfully ingested {len(chunks)} chunks",
        }

    def status(self) -> dict:
        count = len(self.vector_store._chunks) if hasattr(self.vector_store, '_chunks') and self.vector_store._chunks else 0
        return {
            "initialized": self.vector_store.is_initialized,
            "chunk_count": count,
            "vector_store_path": str(settings.vector_store_path),
        }

    def ingest_all(self) -> dict:
        kb_path = settings.knowledge_base_path
        md_files = sorted(kb_path.glob("*.md"))
        if not md_files:
            raise FileNotFoundError(f"No markdown files found in {kb_path}")

        total_chunks = 0
        files_processed = 0
        for md_file in md_files:
            path = str(md_file)
            chunks = self.loader.load(path)
            if not chunks:
                continue
            texts = [c.content for c in chunks]
            metadata = [c.metadata for c in chunks]
            source_name = md_file.name
            for m in metadata:
                m["source"] = source_name
            self.vector_store.add(texts, metadata)
            total_chunks += len(chunks)
            files_processed += 1

        return {
            "status": "success",
            "total_chunks": total_chunks,
            "files_processed": files_processed,
            "message": f"Ingested {total_chunks} chunks from {files_processed} file(s)",
        }

    def rebuild(self) -> dict:
        old_count = 0
        if hasattr(self.vector_store, "_chunks") and self.vector_store._chunks:
            old_count = len(self.vector_store._chunks)
        self.vector_store.delete()
        result = self.ingest_all()
        result["old_chunks_cleared"] = old_count
        return result

    def clear(self):
        self.vector_store.delete()
