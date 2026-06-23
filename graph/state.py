from typing import Annotated, TypedDict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class MultiAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

    user_id: str | None
    session_id: str | None
    assistant_id: str | None

    # Roteamento
    decision: dict | None
    service_target: str | None
    active_flow: str | None
    flow_step: str | None
    flow_data: dict | None
