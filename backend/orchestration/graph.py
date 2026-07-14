import json
import logging
from typing import AsyncIterator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.orchestration.state import ConversationState
from backend.orchestration.nodes.classify import build_classify_node
from backend.orchestration.nodes.retrieve import build_retrieve_node
from backend.orchestration.nodes.route import build_route_node
from backend.orchestration.nodes.generate import build_generate_node
from backend.orchestration.nodes import answers as answer_nodes
from backend.ports.vector_store import VectorStore
from backend.errors import log_exception

logger = logging.getLogger("gigacorp.graph")


INTENT_NODES = {
    "refund": answer_nodes.answer_refund,
    "shipping": answer_nodes.answer_shipping,
    "warranty": answer_nodes.answer_warranty,
    "password": answer_nodes.answer_password,
    "upgrade": answer_nodes.answer_upgrade,
    "cancellation": answer_nodes.answer_cancellation,
    "billing": answer_nodes.answer_billing,
    "trial": answer_nodes.answer_trial,
    "privacy": answer_nodes.answer_privacy,
    "contact": answer_nodes.answer_contact,
    "pricing": answer_nodes.answer_pricing,
    "licensing": answer_nodes.answer_licensing,
    "sla": answer_nodes.answer_sla,
    "nonprofit": answer_nodes.answer_nonprofit,
    "order_status": answer_nodes.answer_order_status,
    "loyalty": answer_nodes.answer_loyalty,
    "invoice": answer_nodes.answer_invoice,
    "return_policy": answer_nodes.answer_return_policy,
    "exchange": answer_nodes.answer_exchange,
    "tracking": answer_nodes.answer_tracking,
    "ticket": answer_nodes.answer_ticket,
    "general": answer_nodes.answer_general,
}


def route_after_classify(state: ConversationState) -> str:
    return state.get("next_node", "retrieve")


def route_after_intent(state: ConversationState) -> str:
    intent = state.get("next_node", "general")
    return intent if intent in INTENT_NODES else "general"


def build_support_graph(vector_store: VectorStore, llm=None, memory=None) -> StateGraph:
    workflow = StateGraph(ConversationState)

    workflow.add_node("classify", build_classify_node())
    workflow.add_node("retrieve", build_retrieve_node(vector_store))
    workflow.add_node("route", build_route_node())
    workflow.add_node("respond_greeting", _build_greeting_node(llm=llm))
    for name in INTENT_NODES:
        workflow.add_node(name, INTENT_NODES[name])
    workflow.add_node("generate", build_generate_node(llm=llm, memory=memory))

    workflow.set_entry_point("classify")

    # Classify → greeting (no RAG) or support (RAG)
    workflow.add_conditional_edges(
        "classify",
        route_after_classify,
        {"respond_greeting": "respond_greeting", "retrieve": "retrieve"},
    )

    # Greeting path: respond → generate → END
    workflow.add_edge("respond_greeting", "generate")
    workflow.add_edge("generate", END)

    # Support path: retrieve → route → intent answer → generate → END
    workflow.add_edge("retrieve", "route")
    workflow.add_conditional_edges(
        "route",
        route_after_intent,
        {name: name for name in INTENT_NODES},
    )
    for name in INTENT_NODES:
        workflow.add_edge(name, "generate")

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


GREETING_RESPONSES: dict[str, str] = {
    "hi": "Hello! I'm GigaBot, your AI support assistant. How can I help you today? Feel free to ask about GigaCorp's products, policies, billing, or services.",
    "hello": "Hi there! Welcome to GigaCorp Support. I can answer questions about our products, policies, and services. What would you like to know?",
    "thanks": "You're welcome! I'm happy to help. Is there anything else you'd like to ask about?",
    "thank you": "You're welcome! If you need anything else, I'm here to help.",
    "bye": "Goodbye! Thank you for reaching out to GigaCorp Support. Feel free to come back anytime if you have more questions.",
    "goodbye": "Goodbye! Have a great day!",
    "good morning": "Good morning! I'm GigaBot, your AI support assistant. How can I assist you today?",
    "good afternoon": "Good afternoon! How can I help you today?",
    "good evening": "Good evening! I'm here to help with any questions about GigaCorp products and services.",
    "how are you": "I'm doing great, thanks for asking! How can I help you today?",
    "default": "Hello! I'm GigaBot, your AI support assistant. How can I help you today?",
}


def _build_greeting_node(llm=None):
    def respond_greeting(state: ConversationState) -> dict:
        query = state.get("query", "").strip().lower()
        user_name = state.get("user_name", "")
        logger.debug("Greeting response for: '%s' (user: %s)", query, user_name or "anonymous")

        if llm:
            try:
                greeting = f"the user ({user_name})" if user_name else "a user"
                prompt = (
                    f"{greeting} said: '{query}'. "
                    f"Respond naturally and warmly as a friendly AI customer support assistant named GigaBot. "
                    f"Keep it concise (1-2 sentences) and invite them to ask about GigaCorp's products and services."
                )
                system = "You are GigaBot, a friendly and professional AI customer support assistant for GigaCorp."
                if user_name:
                    system += f" The user's name is {user_name}. Use their name occasionally to personalize responses."
                answer = llm.generate(
                    prompt,
                    system_prompt=system,
                )
                return {"answer": answer, "sources": []}
            except Exception as e:
                log_exception(e, "greeting_node.llm")
                pass

        answer = GREETING_RESPONSES.get("default")
        for key, response in GREETING_RESPONSES.items():
            if key in query and key != "default":
                answer = response
                break

        if user_name and answer.startswith("Hello"):
            answer = f"Hello, {user_name}! I'm GigaBot, your AI support assistant. How can I help you today?"
        elif user_name and answer.startswith("Hi"):
            answer = f"Hi {user_name}! Welcome to GigaCorp Support. What can I help you with?"

        return {"answer": answer, "sources": []}

    return respond_greeting


LLM_UNAVAILABLE_MSG = (
    "I'm sorry, I'm unable to generate a response right now. "
    "Please try again in a moment."
)


class SupportGraph:
    def __init__(self, vector_store: VectorStore, memory_backend, llm=None):
        self.vector_store = vector_store
        self.memory = memory_backend
        self.llm = llm
        self.graph = build_support_graph(vector_store, llm=llm, memory=memory_backend)

    def query(self, session_id: str, message: str, user_info: dict | None = None) -> dict:
        try:
            self.memory.add_turn(session_id, "user", message)
        except Exception as e:
            logger.warning("Failed to store user message for session %s: %s", session_id, e)

        history_messages = self.get_history(session_id)
        history_str = "\n".join(
            f"{'Customer' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in history_messages[-6:]
        )

        discussed_entities: dict = {}
        if hasattr(self.memory, "get_state"):
            try:
                previous_state = self.memory.get_state(session_id)
                if isinstance(previous_state, dict):
                    discussed_entities = previous_state.get("discussed_entities", {}) or {}
            except Exception as e:
                logger.debug("Could not load state for session %s: %s", session_id, e)

        customer_data = (user_info or {}).get("customer_data", {}) or {}
        initial_state: ConversationState = {
            "messages": [],
            "session_id": session_id,
            "query": message,
            "retrieved_docs": [],
            "context": "",
            "intent": None,
            "answer": "",
            "sources": [],
            "next_node": "",
            "history_str": history_str,
            "user_name": user_info.get("display_name", "") if user_info else "",
            "user_company": user_info.get("company", "") if user_info else "",
            "customer_data": customer_data,
            "discussed_entities": discussed_entities,
        }
        config = {"configurable": {"thread_id": session_id}}

        try:
            result = self.graph.invoke(initial_state, config=config)
        except Exception as e:
            log_exception(e, "SupportGraph.query.graph_invoke")
            logger.error("Graph execution failed for session %s: %s", session_id, e)
            result = {"answer": LLM_UNAVAILABLE_MSG, "sources": []}

        answer = result.get("answer", "")
        sources = result.get("sources", [])

        updated_discussed = result.get("discussed_entities")
        if updated_discussed and hasattr(self.memory, "update_state"):
            try:
                self.memory.update_state(session_id, {"discussed_entities": updated_discussed})
            except Exception as e:
                logger.debug("Could not save discussed_entities for session %s: %s", session_id, e)

        try:
            self.memory.add_turn(session_id, "assistant", answer)
        except Exception as e:
            logger.warning("Failed to store assistant message for session %s: %s", session_id, e)

        return {"answer": answer, "sources": sources}

    async def query_stream(self, session_id: str, message: str, user_info: dict | None = None) -> AsyncIterator[str]:
        try:
            result = self.query(session_id, message, user_info=user_info)
        except Exception as e:
            log_exception(e, "SupportGraph.query_stream")
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Failed to process query'})}\n\n"
            return

        answer = result.get("answer", "")
        sources = result.get("sources", [])
        yield json.dumps({'type': 'sources', 'sources': sources})
        for token in self._tokenize(answer):
            yield json.dumps({'type': 'token', 'content': token})
        yield json.dumps({'type': 'done', 'session_id': session_id})

    async def query_stream_llm(self, session_id: str, message: str, user_info: dict | None = None) -> AsyncIterator[str]:
        if not self.llm:
            async for chunk in self.query_stream(session_id, message, user_info=user_info):
                yield chunk
            return

        try:
            result = self.query(session_id, message, user_info=user_info)
        except Exception as e:
            log_exception(e, "SupportGraph.query_stream_llm")
            yield json.dumps({'type': 'error', 'detail': 'Failed to process query'})
            return

        sources = result.get("sources", [])
        yield json.dumps({'type': 'sources', 'sources': sources})
        answer = result.get("answer", "")
        for token in self._tokenize(answer):
            yield json.dumps({'type': 'token', 'content': token})
        yield json.dumps({'type': 'done', 'session_id': session_id})

    def _tokenize(self, text: str) -> list[str]:
        if not text:
            return [""]
        tokens = []
        words = text.split(" ")
        for i, word in enumerate(words):
            if i == 0:
                for ch in word:
                    tokens.append(ch)
                tokens.append(" ")
            else:
                tokens.append(word + (" " if i < len(words) - 1 else ""))
        return tokens

    def retrieval_diagnostics(self, query: str, k: int = 4, threshold: float = 0.0) -> dict:
        try:
            results = self.vector_store.search(query, k=k, score_threshold=threshold)
        except Exception as e:
            log_exception(e, "SupportGraph.retrieval_diagnostics")
            return {"query": query, "total_results": 0, "threshold": threshold, "results": []}

        docs = [
            {
                "content": r.content,
                "score": r.score,
                "source": r.source,
                "metadata": r.metadata,
            }
            for r in results
        ]
        return {
            "query": query,
            "total_results": len(docs),
            "threshold": threshold,
            "results": docs,
        }

    def list_sessions(self) -> list[str]:
        try:
            return self.memory.list_sessions()
        except Exception as e:
            logger.error("Failed to list sessions: %s", e)
            return []

    def get_history(self, session_id: str) -> list[dict]:
        try:
            return self.memory.get_messages(session_id)
        except Exception as e:
            logger.error("Failed to get history for session %s: %s", session_id, e)
            return []
