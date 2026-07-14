import pickle
import logging
import numpy as np
from pathlib import Path
from typing import Optional

from backend.ports.vector_store import VectorStore, SearchResult
from backend.config import settings
from backend.errors import VectorStoreError, EmbeddingError, log_exception

logger = logging.getLogger("gigacorp.vector_store")


class FAISSAdapter(VectorStore):
    def __init__(self, embedding_model):
        self._embedding_model = embedding_model
        self._index = None
        self._chunks: list[str] = []
        self._metadata: list[dict] = []
        self._storage_path: Path = settings.vector_store_path
        self._dimension = self._embedding_model.dimension
        self._load()

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            return self._embedding_model.embed(texts)
        except EmbeddingError:
            raise
        except Exception as e:
            log_exception(e, "FAISSAdapter.embed")
            raise EmbeddingError("Failed to generate embeddings for FAISS", cause=e)

    def add(self, texts: list[str], metadata: Optional[list[dict]] = None) -> None:
        if metadata is None:
            metadata = [{"source": "knowledge_base"} for _ in texts]
        try:
            embeddings = self._embedding_model.embed(texts)
            emb_array = np.array(embeddings, dtype=np.float32)
            import faiss
            faiss.normalize_L2(emb_array)
            if self._index is None:
                self._index = faiss.IndexFlatIP(self._dimension)
            self._index.add(emb_array)
            self._chunks.extend(texts)
            self._metadata.extend(metadata)
            self._save()
        except EmbeddingError:
            raise
        except ImportError as e:
            logger.error("FAISS library not available: %s", e)
            raise VectorStoreError("FAISS library is not installed", cause=e)
        except Exception as e:
            log_exception(e, "FAISSAdapter.add")
            raise VectorStoreError("Failed to add documents to vector store", cause=e)

    def search(self, query: str, k: Optional[int] = None, score_threshold: Optional[float] = None) -> list[SearchResult]:
        k = k or settings.top_k_retrieval
        threshold = score_threshold if score_threshold is not None else settings.similarity_threshold
        if self._index is None or self._index.ntotal == 0:
            return []
        try:
            query_vec = np.array(self._embedding_model.embed([query]), dtype=np.float32)
            import faiss
            faiss.normalize_L2(query_vec)
            scores, indices = self._index.search(query_vec, k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or score < threshold:
                    continue
                results.append(SearchResult(
                    content=self._chunks[idx],
                    score=float(score),
                    source=self._metadata[idx].get("source", "unknown"),
                    metadata=self._metadata[idx],
                ))
            return results
        except EmbeddingError:
            raise
        except Exception as e:
            log_exception(e, "FAISSAdapter.search")
            raise VectorStoreError("Failed to search vector store", cause=e)

    def delete(self) -> None:
        self._index = None
        self._chunks = []
        self._metadata = []
        try:
            for p in self._storage_path.glob("faiss_*"):
                p.unlink()
        except Exception as e:
            logger.warning("Error cleaning FAISS files: %s", e)

    @property
    def is_initialized(self) -> bool:
        return self._index is not None and self._index.ntotal > 0

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    def _save(self) -> None:
        try:
            self._storage_path.mkdir(parents=True, exist_ok=True)
            import faiss
            faiss.write_index(self._index, str(self._storage_path / "faiss_index.bin"))
            with open(self._storage_path / "faiss_chunks.pkl", "wb") as f:
                pickle.dump(self._chunks, f)
            with open(self._storage_path / "faiss_metadata.pkl", "wb") as f:
                pickle.dump(self._metadata, f)
        except Exception as e:
            log_exception(e, "FAISSAdapter._save")
            raise VectorStoreError("Failed to persist vector store to disk", cause=e)

    def _load(self) -> None:
        index_path = self._storage_path / "faiss_index.bin"
        chunk_path = self._storage_path / "faiss_chunks.pkl"
        meta_path = self._storage_path / "faiss_metadata.pkl"
        if not all(p.exists() for p in [index_path, chunk_path, meta_path]):
            return
        try:
            import faiss
            self._index = faiss.read_index(str(index_path))
            with open(chunk_path, "rb") as f:
                self._chunks = pickle.load(f)
            with open(meta_path, "rb") as f:
                self._metadata = pickle.load(f)
        except Exception as e:
            logger.warning("Failed to load existing FAISS index, starting fresh: %s", e)
            self._index = None
            self._chunks = []
            self._metadata = []
