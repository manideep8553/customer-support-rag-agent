from typing import TypedDict, Optional, Annotated, List
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


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
