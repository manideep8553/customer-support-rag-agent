import logging
from typing import Optional

from backend.cache import embedding_cache
from backend.config import settings
from backend.errors import EmbeddingError, VectorStoreError, log_exception
from backend.ports.vector_store import SearchResult, VectorStore

logger = logging.getLogger("gigacorp.vector_store")


class ChromaDBAdapter(VectorStore):
    def __init__(self, embedding_model):
        self._embedding_model = embedding_model
        self._persist_dir = settings.vector_store_path
        self._collection = None
        self._client = None
        self._ready = False
        self._init_client()

    def _init_client(self) -> None:
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(self._persist_dir))
            self._collection = self._client.get_or_create_collection(
                name="gigacorp_kb",
                metadata={"hnsw:space": "cosine"},
            )
            self._ready = True
        except ImportError:
            logger.warning("chromadb not installed. Install with: pip install chromadb")
            self._ready = False
        except Exception as e:
            logger.error("Failed to initialize ChromaDB: %s", e)
            log_exception(e, "ChromaDBAdapter._init_client")
            self._ready = False

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            return self._embedding_model.embed(texts)
        except EmbeddingError:
            raise
        except Exception as e:
            log_exception(e, "ChromaDBAdapter.embed")
            raise EmbeddingError("Failed to generate embeddings for ChromaDB", cause=e)

    def add(self, texts: list[str], metadata: Optional[list[dict]] = None) -> None:
        if not self._ready:
            raise VectorStoreError("ChromaDB is not initialized")
        if metadata is None:
            metadata = [{"source": "knowledge_base"} for _ in texts]
        try:
            embeddings = self._embedding_model.embed(texts)
            ids = [f"chunk_{i}" for i in range(len(texts))]
            self._collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadata,
                ids=ids,
            )
        except EmbeddingError:
            raise
        except Exception as e:
            log_exception(e, "ChromaDBAdapter.add")
            raise VectorStoreError("Failed to add documents to ChromaDB", cause=e)

    def _embed_query(self, query: str) -> list[list[float]]:
        cached = embedding_cache.get(query)
        if cached is not None:
            return [cached]
        vec = self._embedding_model.embed([query])[0]
        embedding_cache.set(query, vec)
        return [vec]

    def search(self, query: str, k: Optional[int] = None, score_threshold: Optional[float] = None) -> list[SearchResult]:
        if not self._ready or self._collection is None:
            return []
        k = k or settings.top_k_retrieval
        threshold = score_threshold if score_threshold is not None else settings.similarity_threshold
        try:
            query_emb = self._embed_query(query)
            results = self._collection.query(
                query_embeddings=query_emb,
                n_results=k,
            )
        except EmbeddingError:
            raise
        except Exception as e:
            log_exception(e, "ChromaDBAdapter.search")
            raise VectorStoreError("Failed to search ChromaDB", cause=e)

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
        if not self._ready or self._client is None:
            return
        try:
            self._client.delete_collection("gigacorp_kb")
            self._collection = self._client.get_or_create_collection(name="gigacorp_kb")
        except Exception as e:
            logger.warning("Error clearing ChromaDB: %s", e)

    @property
    def is_initialized(self) -> bool:
        return self._ready and self._collection is not None and self._collection.count() > 0

    @property
    def chunk_count(self) -> int:
        if not self._ready or self._collection is None:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0
