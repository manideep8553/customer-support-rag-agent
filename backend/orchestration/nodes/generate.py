from backend.orchestration.state import ConversationState


def build_generate_node():
    def generate(state: ConversationState) -> dict:
        docs = state.get("retrieved_docs", [])
        sources = [
            {
                "content": d["content"][:200],
                "score": d["score"],
                "source": d["source"],
            }
            for d in docs
        ]
        answer = state.get("answer", "")
        if not answer and not docs:
            answer = (
                "I don't have enough information to answer that question. "
                "Please contact our support team at support@gigacorp.com for further assistance."
            )
        return {"answer": answer, "sources": sources}
    return generate
