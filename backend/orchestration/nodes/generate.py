import logging

from backend.orchestration.state import ConversationState
from backend.config import settings
from backend.errors import log_exception
from backend.cache import response_cache, token_cache
from backend.security import reinforce_grounding
from backend.orchestration.nodes.answers import (
    answer_refund, answer_shipping, answer_contact,
    answer_warranty, answer_password, answer_upgrade,
    answer_cancellation, answer_billing, answer_trial,
    answer_privacy, answer_pricing, answer_licensing,
    answer_sla, answer_nonprofit, answer_general,
    answer_order_status, answer_loyalty,
    answer_invoice, answer_return_policy, answer_exchange,
    answer_tracking, answer_ticket,
)

logger = logging.getLogger("gigacorp.generate")

RAG_SYSTEM_PROMPT = """You are GigaBot, an AI customer support representative for GigaCorp. You are helpful, professional, and concise.

Company: GigaCorp \u2014 a global technology company offering cloud computing, AI analytics, and enterprise software.

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
9. After every factual statement derived from the knowledge base, cite the source using the exact format shown in the retrieved knowledge, which includes the document name and section: [Source N: DocumentName \u2192 SectionHeading]. Always replicate the full citation.
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

NO_INFO_MSG = (
    "I don't have enough information to answer that question. "
    "Please contact our support team at support@gigacorp.com for further assistance."
)


def _estimate_tokens(text: str, llm) -> int:
    cached = token_cache.get(text)
    if cached is not None:
        return cached
    if hasattr(llm, "count_tokens"):
        try:
            count = llm.count_tokens(text)
            token_cache.set(text, count)
            return count
        except Exception:
            pass
    count = len(text.split())
    token_cache.set(text, count)
    return count


def _build_history(memory, session_id: str, llm, query: str) -> str:
    try:
        messages = memory.get_messages(session_id)
    except Exception as e:
        logger.warning("Failed to get messages for session %s: %s", session_id, e)
        messages = []

    try:
        summary = memory.get_summary(session_id)
    except Exception as e:
        logger.warning("Failed to get summary for session %s: %s", session_id, e)
        summary = ""

    if not messages and not summary:
        return ""

    token_budget = settings.max_history_tokens

    def format_line(msg: dict) -> str:
        role = "Customer" if msg["role"] == "user" else "Assistant"
        return f"{role}: {msg['content']}"

    recent_lines = [format_line(m) for m in messages]
    summary_line = f"[Previous conversation summary: {summary}]" if summary else ""

    answer_note = "\n[Note: The current turn's assistant answer will be shown here after generation.]"

    def total_tokens(summary_line: str, lines: list[str], query: str) -> int:
        parts = []
        if summary_line:
            parts.append(summary_line)
        parts.extend(lines)
        parts.append(f"Customer: {query}")
        parts.append(answer_note)
        return _estimate_tokens("\n".join(parts), llm)

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
                try:
                    memory.summarize(session_id, new_summary)
                except Exception as e:
                    logger.warning("Failed to persist summary for session %s: %s", session_id, e)
                summary = new_summary
                summary_line = f"[Previous conversation summary: {summary}]"
        except Exception as e:
            logger.warning("Summarization failed for session %s: %s", session_id, e)
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


def _build_rag_prompt(query: str, context: str, history: str, user_name: str = "", user_company: str = "", customer_data: dict | None = None) -> tuple[str, str]:
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
    system = RAG_SYSTEM_PROMPT
    if user_name:
        system += f"\n\nThe user's name is {user_name}. Use their name occasionally to personalize responses."
    if user_company:
        system += f"\n\nThe user is from {user_company}. Reference their company when relevant."
    if customer_data:
        orders = customer_data.get("recent_orders", [])
        subs = customer_data.get("subscriptions", [])
        loyalty = customer_data.get("loyalty", {})
        addr = customer_data.get("default_address", {})
        system += "\n\n--- CUSTOMER DATA (for personalized responses) ---\n"
        system += f"Customer ID: {customer_data.get('customer_id', 'N/A')}\n"
        system += f"Account Status: {customer_data.get('account_status', 'N/A')}\n"
        system += f"Phone: {customer_data.get('phone', 'N/A')}\n"
        if loyalty:
            system += f"Loyalty Tier: {loyalty.get('tier', 'N/A').title()} ({loyalty.get('points', 0)} points)\n"
        if addr:
            system += f"Default Shipping Address: {addr.get('street_line1', '')}, {addr.get('city', '')}, {addr.get('state', '')} {addr.get('postal_code', '')}, {addr.get('country', '')}\n"
        if subs:
            system += "Active Subscriptions:\n"
            for s in subs:
                system += f"  - {s['plan_name']} (${s['amount']:.2f}/{s['billing_cycle']})\n"
        if orders:
            system += "Recent Orders:\n"
            for o in orders[:2]:
                items_str = ", ".join(i['product_name'] for i in o.get('items', []))
                system += f"  - {o['order_number']}: {o['status'].title()} - {items_str}\n"
        system += "\nUse this customer data to provide personalized responses when relevant. Do not fabricate data not present here."
    return system, user_prompt


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


LLM_UNAVAILABLE_MSG = (
    "I'm sorry, I'm unable to generate a response right now. "
    "Please try again in a moment."
)

INTENT_ANSWER_FN: dict[str, callable] = {
    "refund": answer_refund,
    "return_policy": answer_return_policy,
    "exchange": answer_exchange,
    "invoice": answer_invoice,
    "shipping": answer_shipping,
    "contact": answer_contact,
    "warranty": answer_warranty,
    "password": answer_password,
    "upgrade": answer_upgrade,
    "cancellation": answer_cancellation,
    "billing": answer_billing,
    "trial": answer_trial,
    "privacy": answer_privacy,
    "pricing": answer_pricing,
    "licensing": answer_licensing,
    "sla": answer_sla,
    "nonprofit": answer_nonprofit,
    "order_status": answer_order_status,
    "loyalty": answer_loyalty,
    "tracking": answer_tracking,
    "ticket": answer_ticket,
    "general": answer_general,
}

INTENT_KEYWORDS: dict[str, list[str]] = {
    "ticket": ["support ticket", "my ticket", "ticket status", "open a ticket",
               "create a ticket", "raise a ticket", "ticket number", "submit a ticket",
               "file a complaint", "report a problem", "my support request"],
    "tracking": ["track package", "track my package", "where is my package",
                 "package location", "shipment status", "my shipment",
                 "tracking update", "where is my shipment", "when will it arrive",
                 "has my order shipped", "package tracking"],
    "invoice": ["invoice for", "get an invoice", "my invoice", "receipt for", "billing history"],
    "refund": ["refund", "money back"],
    "return_policy": ["return policy", "how to return", "return an item", "rma", "return label"],
    "exchange": ["exchange", "swap", "replace", "different product", "different size"],
    "order_status": ["track my order", "where is my order", "order status", "tracking number", "cancel my order", "cancel my pending", "what happened to ord", "order number"],
    "loyalty": ["loyalty", "points", "rewards", "loyalty tier", "my tier", "my points"],
    "refund": ["refund", "money back"],
    "shipping": ["shipping", "delivery", "ship"],
    "contact": ["contact", "support", "phone", "email support", "customer service", "talk to"],
    "pricing": ["price", "cost", "pricing", "how much"],
    "billing": ["bill", "payment", "subscription"],
    "warranty": ["warrant"],
    "password": ["password", "reset"],
    "upgrade": ["upgrade", "downgrade"],
    "cancellation": ["cancel account", "close account", "delete account"],
    "trial": ["trial", "free"],
    "privacy": ["privacy", "gdpr", "data"],
    "licensing": ["license"],
    "sla": ["sla", "uptime"],
    "nonprofit": ["nonprofit", "non-profit", "discount"],
}


def _match_fast_intent(query: str) -> str | None:
    q = query.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return intent
    return None


def build_generate_node(llm=None, memory=None):
    def generate(state: ConversationState) -> dict:
        docs = state.get("retrieved_docs", [])
        query = state.get("query", "")
        context = state.get("context", "")
        has_relevant = bool(docs)
        session_id = state.get("session_id", "")
        user_name = state.get("user_name", "")
        user_company = state.get("user_company", "")
        customer_data = state.get("customer_data", {}) or {}

        # Pass through pre-set answer (e.g., from greeting handler, error fallback)
        existing_answer = state.get("answer", "")
        if existing_answer:
            sources = _format_sources(docs)
            return {"answer": existing_answer, "sources": sources}

        # Fast-path: rule-based answer for known intents (no LLM call needed)
        intent = state.get("intent", "") or _match_fast_intent(query) or ""
        if not llm or not has_relevant:
            if intent in INTENT_ANSWER_FN:
                sources = _format_sources(docs)
                result = INTENT_ANSWER_FN[intent](state)
                answer = result.get("answer", "")
                # Personalize rule-based answer with user name
                if user_name:
                    if answer.startswith("Here are"):
                        answer = answer.replace("Here are", f"Here are, {user_name},")
                    elif answer.startswith("According"):
                        answer = answer.replace("According to GigaCorp", f"According to GigaCorp's policies, {user_name},")
                    elif answer.startswith("Your") or answer.startswith("Per"):
                        pass
                return {"answer": answer, "sources": sources}

        if llm and has_relevant:
            context_preview = context[:200] if context else ""

            # Check response cache
            cached = response_cache.get(session_id, query, context_preview)
            if cached is not None:
                sources = _format_sources(docs)
                return {"answer": cached, "sources": sources}

            answer = LLM_UNAVAILABLE_MSG
            try:
                safe_query = reinforce_grounding(query)
                history = _build_history(memory, session_id, llm, safe_query)
                system_prompt, user_prompt = _build_rag_prompt(safe_query, context, history, user_name, user_company, customer_data)
                answer = llm.generate(user_prompt, system_prompt=system_prompt)
                response_cache.set(session_id, query, context_preview, answer)
            except Exception as e:
                log_exception(e, "generate_node.llm_generate")
                if answer.startswith("I'm sorry") or answer.startswith("I don't have"):
                    pass
                else:
                    answer = LLM_UNAVAILABLE_MSG
        elif llm and not has_relevant:
            answer = NO_INFO_MSG
        else:
            answer = state.get("answer", "")
            if not answer and not has_relevant:
                answer = NO_INFO_MSG

        sources = _format_sources(docs)
        return {"answer": answer, "sources": sources}
    return generate
