import json
import logging
from typing import Literal, AsyncIterator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.orchestration.state import ConversationState
from backend.orchestration.nodes.retrieve import build_retrieve_node
from backend.orchestration.nodes.route import build_route_node
from backend.orchestration.nodes.generate import build_generate_node
from backend.orchestration.nodes import answers as answer_nodes
from backend.ports.vector_store import VectorStore

logger = logging.getLogger("gigacorp.graph")


_SYSTEM_PROMPT = """You are GigaBot, an AI customer support representative for GigaCorp. You are helpful, professional, and concise.

Your responsibilities:
- Answer customer questions about GigaCorp products, policies, and services
- Provide accurate information based solely on the provided context
- Cite sources when referencing specific policies
- Be empathetic and professional in tone
- If you don't know the answer, say so honestly — do not make up information
- Keep responses focused and avoid unnecessary details

Company: GigaCorp — a global technology company offering cloud computing, AI analytics, and enterprise software."""

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
    "general": answer_nodes.answer_general,
}


def route_after_classify(state: ConversationState) -> str:
    intent = state.get("next_node", "general")
    return intent if intent in INTENT_NODES else "general"


def build_support_graph(vector_store: VectorStore) -> StateGraph:
    workflow = StateGraph(ConversationState)
    workflow.add_node("retrieve", build_retrieve_node(vector_store))
    workflow.add_node("route", build_route_node())
    for name in INTENT_NODES:
        workflow.add_node(name, INTENT_NODES[name])
    workflow.add_node("generate", build_generate_node())
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "route")
    workflow.add_conditional_edges("route", route_after_classify, {name: name for name in INTENT_NODES})
    for name in INTENT_NODES:
        workflow.add_edge(name, "generate")
    workflow.add_edge("generate", END)
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


class SupportGraph:
    def __init__(self, vector_store: VectorStore, memory_backend, llm=None):
        self.vector_store = vector_store
        self.memory = memory_backend
        self.llm = llm
        self.graph = build_support_graph(vector_store)

    def query(self, session_id: str, message: str) -> dict:
        history = self.memory.get_history(session_id)
        self.memory.add_turn(session_id, "user", message)
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
        }
        config = {"configurable": {"thread_id": session_id}}
        result = self.graph.invoke(initial_state, config=config)
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        self.memory.add_turn(session_id, "assistant", answer)
        return {"answer": answer, "sources": sources}

    async def query_stream(self, session_id: str, message: str) -> AsyncIterator[str]:
        result = self.query(session_id, message)
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
        for token in self._tokenize(answer):
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

    async def query_stream_llm(self, session_id: str, message: str) -> AsyncIterator[str]:
        if not self.llm:
            async for chunk in self.query_stream(session_id, message):
                yield chunk
            return
        history = self.memory.get_history(session_id)
        self.memory.add_turn(session_id, "user", message)
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
        }
        config = {"configurable": {"thread_id": session_id}}
        result = self.graph.invoke(initial_state, config=config)
        sources = result.get("sources", [])
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
        retrieved_docs = result.get("retrieved_docs", [])
        context = result.get("context", "")
        prompt = f"""{_SYSTEM_PROMPT}

{"=" * 60}
CONVERSATION HISTORY:
{history}
{"=" * 60}

RETRIEVED KNOWLEDGE:
{context}
{"=" * 60}

Current customer query: {message}

Instructions:
- Answer using ONLY the retrieved knowledge above.
- If the knowledge doesn't contain enough information, say: "I don't have enough information to answer that question. Please contact our support team at support@gigacorp.com for further assistance."
- Reference relevant sources when citing specific policies.
- Keep answers concise and direct.

Answer:"""
        answer_parts = []
        async for token in self.llm.stream(prompt, system_prompt=_SYSTEM_PROMPT):
            answer_parts.append(token)
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        answer = "".join(answer_parts)
        self.memory.add_turn(session_id, "assistant", answer)
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

    def _tokenize(self, text: str) -> list[str]:
        tokens = []
        for word in text.split(" "):
            tokens.append(word + " ")
        if tokens:
            tokens[-1] = tokens[-1].rstrip(" ")
        return tokens or [""]

    def list_sessions(self) -> list[str]:
        return self.memory.list_sessions()

    def get_history(self, session_id: str) -> list[dict]:
        return self.memory.get_messages(session_id)
