from backend.orchestration.state import ConversationState
from backend.config import settings

RAG_SYSTEM_PROMPT = """You are GigaBot, an AI customer support representative for GigaCorp. You are helpful, professional, and concise.

Company: GigaCorp — a global technology company offering cloud computing, AI analytics, and enterprise software.

CRITICAL INSTRUCTIONS — You MUST follow these:
1. Answer using ONLY the retrieved knowledge provided below under "RETRIEVED KNOWLEDGE".
2. If the retrieved knowledge does not contain sufficient information to fully answer the question, state clearly: "I don't have enough information to answer that question. Please contact our support team at support@gigacorp.com for further assistance." Do NOT try to make up an answer.
3. NEVER invent, guess, or fabricate any policies, prices, features, or procedures not present in the retrieved knowledge.
4. When referencing specific policies or data from the knowledge base, cite the source using the [Source N] notation shown in the retrieved knowledge.
5. Keep responses concise, direct, and professional.
6. Do not repeat the user's question back to them.

CONVERSATION CONTEXT — Use the conversation history to understand follow-up questions. For example, if a user previously asked about shipping to a specific country and then asks "How much does it cost there?", you should infer "there" refers to the previously mentioned country. Resolve pronouns, implicit references, and contextual ellipsis using the conversation history."""

SUMMARIZATION_PROMPT = """You are an AI assistant summarizing a customer support conversation for GigaCorp.

Please summarize the following conversation exchange, keeping only the key information:
- What products/services the customer asked about
- What policies were discussed
- What decisions or agreements were made
- Any specific details (countries, prices, timelines) mentioned

Keep the summary brief (2-4 sentences) and factual. Do not add information not present in the conversation.

Conversation to summarize:
{conversation_text}

Summary:"""


def _build_history(memory, session_id: str, llm, query: str) -> str:
    messages = memory.get_messages(session_id)
    if not messages and not memory.get_summary(session_id):
        return ""

    summary = memory.get_summary(session_id)
    token_budget = settings.max_history_tokens

    def format_line(msg: dict) -> str:
        role = "Customer" if msg["role"] == "user" else "Assistant"
        return f"{role}: {msg['content']}"

    def format_lines(lines: list[str]) -> str:
        return "\n".join(lines)

    recent_lines = [format_line(m) for m in messages]
    summary_line = f"[Previous conversation summary: {summary}]" if summary else ""

    def estimate_tokens(text: str) -> int:
        if hasattr(llm, "count_tokens"):
            return llm.count_tokens(text)
        return len(text.split())

    answer_note = "\n[Note: The current turn's assistant answer will be shown here after generation.]"

    def total_tokens(summary_line: str, lines: list[str], query: str) -> int:
        parts = []
        if summary_line:
            parts.append(summary_line)
        parts.extend(lines)
        parts.append(f"Customer: {query}")
        parts.append(answer_note)
        return estimate_tokens("\n".join(parts))

    current_total = total_tokens(summary_line, recent_lines, query)

    if current_total <= token_budget:
        parts = []
        if summary_line:
            parts.append(summary_line)
        parts.extend(recent_lines)
        return "\n".join(parts)

    turn_count = len(messages) // 2
    if turn_count >= settings.summarization_threshold_turns and summary:
        n_keep = max(4, len(recent_lines) - 6)
        kept = recent_lines[-n_keep:]
        attempt_total = total_tokens(summary_line, kept, query)
        while len(kept) > 2 and attempt_total > token_budget:
            kept = kept[2:]
            attempt_total = total_tokens(summary_line, kept, query)
        parts = []
        if summary_line:
            parts.append(summary_line)
        parts.extend(kept)
        return "\n".join(parts)

    n_keep = len(recent_lines)
    attempt_total = current_total
    while n_keep > 2 and attempt_total > token_budget:
        n_keep -= 2
        kept = recent_lines[-n_keep:]
        attempt_total = total_tokens(summary_line, kept, query)
    kept = recent_lines[-n_keep:]
    to_summarize = recent_lines[:-n_keep] if n_keep < len(recent_lines) else []

    if to_summarize and turn_count >= settings.summarization_threshold_turns:
        conversation_text = "\n".join(to_summarize)
        summary_prompt = SUMMARIZATION_PROMPT.format(conversation_text=conversation_text)
        try:
            new_summary = llm.generate(summary_prompt, system_prompt=None)
            new_summary = new_summary.strip()
            if new_summary:
                if summary:
                    new_summary = f"{summary} | {new_summary}"
                memory.summarize(session_id, new_summary)
                summary = new_summary
                summary_line = f"[Previous conversation summary: {summary}]"
        except Exception:
            pass
        kept = recent_lines[-min(n_keep, len(recent_lines)):]
        attempt_total = total_tokens(summary_line, kept, query)
        while len(kept) > 2 and attempt_total > token_budget:
            kept = kept[2:]
            attempt_total = total_tokens(summary_line, kept, query)

    parts = []
    if summary_line:
        parts.append(summary_line)
    parts.extend(kept)
    return "\n".join(parts)


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
- Use the conversation history to resolve any ambiguous references in the current question (e.g., "there", "it", "that policy").
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


def build_generate_node(llm=None, memory=None):
    def generate(state: ConversationState) -> dict:
        docs = state.get("retrieved_docs", [])
        query = state.get("query", "")
        context = state.get("context", "")
        has_relevant = bool(docs)
        session_id = state.get("session_id", "")

        if llm and has_relevant:
            history = _build_history(memory, session_id, llm, query)
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
