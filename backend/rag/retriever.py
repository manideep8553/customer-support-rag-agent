import pickle
import numpy as np
from scipy.sparse import csr_matrix, vstack
from pathlib import Path
from typing import Optional

from backend.config import settings
from backend.rag.embedding import EmbeddingService


class Retriever:
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.doc_matrix: Optional[csr_matrix] = None
        self.chunks: list[str] = []
        self.metadata: list[dict] = []
        self._load_index()

    def _index_path(self) -> Path:
        return settings.vector_store_path / "tfidf_index.pkl"

    def _chunks_path(self) -> Path:
        return settings.vector_store_path / "chunks.pkl"

    def _metadata_path(self) -> Path:
        return settings.vector_store_path / "metadata.pkl"

    def index_exists(self) -> bool:
        return self._index_path().exists()

    def build_index(self, chunks: list[str], metadata: Optional[list[dict]] = None):
        self.chunks = chunks
        self.metadata = metadata or [{"source": "knowledge_base"} for _ in chunks]

        self.embedding_service.fit(chunks)
        self.doc_matrix = self.embedding_service.embed_sparse(chunks)

        settings.vector_store_path.mkdir(parents=True, exist_ok=True)
        with open(self._index_path(), "wb") as f:
            pickle.dump(self.doc_matrix, f)
        with open(self._chunks_path(), "wb") as f:
            pickle.dump(self.chunks, f)
        with open(self._metadata_path(), "wb") as f:
            pickle.dump(self.metadata, f)

        self.embedding_service.save(settings.vector_store_path)

    def _load_index(self):
        if not self.index_exists():
            self.doc_matrix = None
            return

        with open(self._index_path(), "rb") as f:
            self.doc_matrix = pickle.load(f)
        with open(self._chunks_path(), "rb") as f:
            self.chunks = pickle.load(f)
        with open(self._metadata_path(), "rb") as f:
            self.metadata = pickle.load(f)
        self.embedding_service.load(settings.vector_store_path)

    def retrieve(self, query: str, k: Optional[int] = None) -> list[dict]:
        k = k or settings.top_k_retrieval

        if self.doc_matrix is None or self.doc_matrix.shape[0] == 0:
            return []
        if not self.embedding_service.is_fitted:
            return []

        query_vec = self.embedding_service.embed_query(query)
        if query_vec.sum() == 0:
            return []

        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)

        doc_norms = np.array(
            [np.linalg.norm(row.toarray()) for row in self.doc_matrix]
        )
        doc_norms = doc_norms / (doc_norms.max() + 1e-10)

        scores = self.doc_matrix.dot(query_vec).flatten()
        scores = scores / (np.linalg.norm(query_vec) + 1e-10)
        doc_lengths = np.array([len(c.split()) for c in self.chunks])
        doc_lengths = doc_lengths / (doc_lengths.max() + 1e-10)
        scores = scores * (0.7 + 0.3 * doc_norms)

        top_indices = np.argsort(scores)[::-1][:k]

        results = []
        for idx in top_indices:
            if scores[idx] <= 0:
                continue
            results.append({
                "content": self.chunks[idx],
                "score": float(min(scores[idx], 1.0)),
                "source": self.metadata[idx].get("source", "unknown"),
            })

        return results

    def clear(self):
        self.doc_matrix = None
        self.chunks = []
        self.metadata = []
        for p in [self._index_path(), self._chunks_path(), self._metadata_path()]:
            if p.exists():
                p.unlink()
