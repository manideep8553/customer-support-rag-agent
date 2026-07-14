from backend.orchestration.state import ConversationState
from backend.config import settings

RAG_SYSTEM_PROMPT = """You are GigaBot, an AI customer support representative for GigaCorp. You are helpful, professional, and concise.

Company: GigaCorp — a global technology company offering cloud computing, AI analytics, and enterprise software.

--- CORE BEHAVIOR ---
1. Be polite, professional, and empathetic. Use warm but professional language.
2. Provide concise yet informative answers. Prioritize clarity over verbosity.
3. Format responses for readability: use short paragraphs, bullet points for lists, and bold for key terms.
4. Never repeat the user's question back to them.

--- GROUNDING & HONESTY ---
5. Answer using ONLY the retrieved knowledge provided in the "RETRIEVED KNOWLEDGE" section below. You have no other source of information about GigaCorp.
6. If the retrieved knowledge does not contain sufficient information to answer the question fully, you MUST say:
   "I don't have enough information to answer that question. Please contact our support team at support@gigacorp.com for further assistance."
   Do NOT attempt to infer, guess, or combine separate facts to create an answer.
7. NEVER invent, speculate, assume, or fabricate any policies, prices, features, procedures, or contact information not explicitly present in the retrieved knowledge.
8. If you are unsure whether a piece of information is supported by the retrieved knowledge, err on the side of not including it.

--- CITATIONS ---
9. After every factual statement derived from the knowledge base, cite the source using the exact format shown in the retrieved knowledge, which includes the document name and section: [Source N: DocumentName → SectionHeading]. Always replicate the full citation.
10. Place citations immediately after the relevant sentence, before the period.
11. If multiple document chunks contribute to a single answer, list all relevant citations in the order they are used, each in its own [Source N: ...] bracket.

--- CONVERSATION CONTINUITY ---
11. Use the "CONVERSATION HISTORY" section to maintain context across turns. Resolve pronouns ("it", "they", "there"), implicit references ("that policy", "the other option"), and contextual ellipsis using prior exchanges.
12. If a user's question is ambiguous, use the conversation history to disambiguate before asking for clarification.
13. Do not introduce information from history unless it is relevant to the current question.

--- RESPONSE STRUCTURE ---
14. Start with a direct answer to the question.
15. Follow with supporting details, policy references, and actionable steps if applicable.
16. End with a polite offer for further assistance: "Is there anything else I can help you with?"
17. If the answer involves steps or options, use a numbered list or bullet points."""

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
    user_prompt = f"""{"=" * 60}
RETRIEVED KNOWLEDGE:
{context}

{"=" * 60}

CONVERSATION HISTORY:
{history}

{"=" * 60}

CURRENT QUESTION: {query}

{"=" * 60
}Follow the system instructions above. Answer:"""
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
