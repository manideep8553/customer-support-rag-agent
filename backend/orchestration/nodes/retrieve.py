import logging

from backend.orchestration.state import ConversationState
from backend.ports.vector_store import VectorStore
from backend.config import settings
from backend.errors import RetrievalError, log_exception, friendly_error

logger = logging.getLogger("gigacorp.retrieve")


def build_retrieve_node(vector_store: VectorStore):
    def retrieve(state: ConversationState) -> dict:
        query = state.get("query", "")
        if not query:
            return {"retrieved_docs": [], "context": ""}
        try:
            results = vector_store.search(
                query,
                k=settings.top_k_retrieval,
                score_threshold=settings.similarity_threshold,
            )
        except Exception as e:
            log_exception(e, "retrieve_node.search")
            logger.warning("Retrieval failed for query '%s': %s. Returning empty results.", query[:50], e)
            return {"retrieved_docs": [], "context": _format_context([])}

        docs = [
            {"content": r.content, "score": r.score, "source": r.source, "metadata": r.metadata}
            for r in results
        ]
        context = _format_context(docs)
        return {"retrieved_docs": docs, "context": context}
    return retrieve


def _format_context(results: list[dict]) -> str:
    if not results:
        return "No relevant documents found."
    sections = []
    for i, r in enumerate(results, 1):
        meta = r.get("metadata", {})
        doc = meta.get("source", r.get("source", "unknown"))
        heading = meta.get("heading", "")
        citation = f"[Source {i}: {doc}"
        if heading:
            citation += f" \u2192 {heading}"
        citation += f"] (Relevance: {r['score']:.2f})"
        sections.append(f"{citation}\n{r['content']}")
    return "\n\n".join(sections)
