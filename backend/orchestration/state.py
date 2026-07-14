from typing import Annotated, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ConversationState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    session_id: str
    query: str
    retrieved_docs: list[dict]
    context: str
    intent: Optional[str]
    answer: str
    sources: list[dict]
    next_node: str
    history_str: str
    user_name: str
    user_company: str
    customer_data: dict
    discussed_entities: dict
