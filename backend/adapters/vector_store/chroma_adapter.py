from pathlib import Path
from typing import Optional

from backend.ports.vector_store import VectorStore, SearchResult
from backend.config import settings


class ChromaDBAdapter(VectorStore):
    def __init__(self, embedding_model):
        self._embedding_model = embedding_model
        self._persist_dir = settings.vector_store_path
        self._collection = None
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(self._persist_dir))
            self._collection = self._client.get_or_create_collection(
                name="gigacorp_kb",
                metadata={"hnsw:space": "cosine"},
            )
        except ImportError:
            raise ImportError("chromadb is required. Install: pip install chromadb")

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._embedding_model.embed(texts)

    def add(self, texts: list[str], metadata: Optional[list[dict]] = None) -> None:
        if metadata is None:
            metadata = [{"source": "knowledge_base"} for _ in texts]
        embeddings = self._embedding_model.embed(texts)
        ids = [f"chunk_{i}" for i in range(len(texts))]
        self._collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadata,
            ids=ids,
        )

    def search(self, query: str, k: Optional[int] = None, score_threshold: Optional[float] = None) -> list[SearchResult]:
        k = k or settings.top_k_retrieval
        threshold = score_threshold if score_threshold is not None else settings.similarity_threshold
        query_emb = self._embedding_model.embed([query])
        results = self._collection.query(
            query_embeddings=query_emb,
            n_results=k,
        )
        output = []
        for i in range(len(results["ids"][0])):
            if "distances" in results:
                distance = float(results["distances"][0][i])
                score = 1.0 - (distance / 2.0)
            else:
                score = 0.0
            if score < threshold:
                continue
            output.append(SearchResult(
                content=results["documents"][0][i],
                score=score,
                source=results["metadatas"][0][i].get("source", "unknown"),
                metadata=results["metadatas"][0][i],
            ))
        return output

    def delete(self) -> None:
        self._client.delete_collection("gigacorp_kb")
        self._collection = self._client.get_or_create_collection(name="gigacorp_kb")

    @property
    def is_initialized(self) -> bool:
        return self._collection is not None and self._collection.count() > 0
