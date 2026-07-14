from backend.orchestration.state import ConversationState

RAG_SYSTEM_PROMPT = """You are GigaBot, an AI customer support representative for GigaCorp. You are helpful, professional, and concise.

Company: GigaCorp — a global technology company offering cloud computing, AI analytics, and enterprise software.

CRITICAL INSTRUCTIONS — You MUST follow these:
1. Answer using ONLY the retrieved knowledge provided below under "RETRIEVED KNOWLEDGE".
2. If the retrieved knowledge does not contain sufficient information to fully answer the question, state clearly: "I don't have enough information to answer that question. Please contact our support team at support@gigacorp.com for further assistance." Do NOT try to make up an answer.
3. NEVER invent, guess, or fabricate any policies, prices, features, or procedures not present in the retrieved knowledge.
4. When referencing specific policies or data from the knowledge base, cite the source using the [Source N] notation shown in the retrieved knowledge.
5. Keep responses concise, direct, and professional.
6. Do not repeat the user's question back to them."""


def _build_rag_prompt(query: str, context: str, history: str) -> tuple[str, str]:
    user_prompt = f"""RETRIEVED KNOWLEDGE:
{context}

{"=" * 60}

CONVERSATION HISTORY:
{history}

{"=" * 60}

CURRENT QUESTION: {query}

Instructions:
- Answer using ONLY the retrieved knowledge above.
- If the knowledge doesn't contain enough information, say: "I don't have enough information to answer that question. Please contact our support team at support@gigacorp.com for further assistance."
- Reference relevant sources when citing specific policies using [Source N].
- Keep answers concise and direct.

Answer:"""
    return RAG_SYSTEM_PROMPT, user_prompt


def _format_sources(docs: list[dict]) -> list[dict]:
    return [
        {
            "content": d["content"],
            "score": d["score"],
            "source": d["source"],
            "metadata": d.get("metadata", {}),
        }
        for d in docs
    ]


def build_generate_node(llm=None):
    def generate(state: ConversationState) -> dict:
        docs = state.get("retrieved_docs", [])
        query = state.get("query", "")
        context = state.get("context", "")
        has_relevant = bool(docs)

        if llm and has_relevant:
            history = state.get("history_str", "")
            system_prompt, user_prompt = _build_rag_prompt(query, context, history)
            answer = llm.generate(user_prompt, system_prompt=system_prompt)
        elif llm and not has_relevant:
            answer = (
                "I don't have enough information to answer that question. "
                "Please contact our support team at support@gigacorp.com for further assistance."
            )
        else:
            answer = state.get("answer", "")
            if not answer and not has_relevant:
                answer = (
                    "I don't have enough information to answer that question. "
                    "Please contact our support team at support@gigacorp.com for further assistance."
                )

        sources = _format_sources(docs)
        return {"answer": answer, "sources": sources}
    return generate
