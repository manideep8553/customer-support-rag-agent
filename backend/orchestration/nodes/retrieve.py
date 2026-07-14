from backend.orchestration.state import ConversationState
from backend.ports.vector_store import VectorStore
from backend.config import settings


def build_retrieve_node(vector_store: VectorStore):
    def retrieve(state: ConversationState) -> dict:
        query = state.get("query", "")
        if not query:
            return {"retrieved_docs": [], "context": ""}
        results = vector_store.search(
            query,
            k=settings.top_k_retrieval,
            score_threshold=settings.similarity_threshold,
        )
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
        heading = r.get("metadata", {}).get("heading", "")
        header = f"[Source {i}] (Relevance: {r['score']:.2f})"
        if heading:
            header += f" — {heading}"
        sections.append(f"{header}\n{r['content']}")
    return "\n\n".join(sections)
