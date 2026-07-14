import json
import logging
from typing import AsyncIterator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.orchestration.state import ConversationState
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
    "general": answer_nodes.answer_general,
}


def route_after_classify(state: ConversationState) -> str:
    intent = state.get("next_node", "general")
    return intent if intent in INTENT_NODES else "general"


def build_support_graph(vector_store: VectorStore, llm=None, memory=None) -> StateGraph:
    workflow = StateGraph(ConversationState)
    workflow.add_node("retrieve", build_retrieve_node(vector_store))
    workflow.add_node("route", build_route_node())
    for name in INTENT_NODES:
        workflow.add_node(name, INTENT_NODES[name])
    workflow.add_node("generate", build_generate_node(llm=llm, memory=memory))
    workflow.set_entry_point("retrieve")
    if llm:
        workflow.add_edge("retrieve", "generate")
    else:
        workflow.add_edge("retrieve", "route")
        workflow.add_conditional_edges("route", route_after_classify, {name: name for name in INTENT_NODES})
        for name in INTENT_NODES:
            workflow.add_edge(name, "generate")
    workflow.add_edge("generate", END)
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


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

    def query(self, session_id: str, message: str) -> dict:
        try:
            self.memory.add_turn(session_id, "user", message)
        except Exception as e:
            logger.warning("Failed to store user message for session %s: %s", session_id, e)

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
            "history_str": "",
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

        try:
            self.memory.add_turn(session_id, "assistant", answer)
        except Exception as e:
            logger.warning("Failed to store assistant message for session %s: %s", session_id, e)

        return {"answer": answer, "sources": sources}

    async def query_stream(self, session_id: str, message: str) -> AsyncIterator[str]:
        try:
            result = self.query(session_id, message)
        except Exception as e:
            log_exception(e, "SupportGraph.query_stream")
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Failed to process query'})}\n\n"
            return

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

        try:
            result = self.query(session_id, message)
        except Exception as e:
            log_exception(e, "SupportGraph.query_stream_llm")
            yield f"data: {json.dumps({'type': 'error', 'detail': 'Failed to process query'})}\n\n"
            return

        sources = result.get("sources", [])
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
        answer = result.get("answer", "")
        for token in self._tokenize(answer):
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

    def _tokenize(self, text: str) -> list[str]:
        if not text:
            return [""]
        tokens = []
        words = text.split(" ")
        for i, word in enumerate(words):
            if i == 0:
                # First token: yield character-by-character for instant perceived latency
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
