"""Typed LangGraph state for the support workflow."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages


class SupportState(TypedDict, total=False):
    """Minimal practical state for the multi-agent support graph."""

    customer_id: str
    conversation_id: str
    message: str
    conversation_history: list[dict[str, str]]
    customer_context: dict[str, Any]
    intent: dict[str, Any]
    priority: str
    assigned_agent: Literal["billing", "technical", "account", "general"]
    tool_results: list[dict[str, Any]]
    resolution: dict[str, Any]
    requires_human: bool
    approval_id: Optional[str]
    approval_status: Optional[str]  # pending|approved|rejected
    final_response: Optional[str]
    ticket_id: Optional[str]
    errors: list[str]
    # Optional LangChain message channel for agents that need it
    messages: Annotated[list, add_messages]
