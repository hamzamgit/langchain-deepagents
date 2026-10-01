"""Compile the LangGraph support workflow with checkpointing for HITL."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph

from app.agents.supervisor import supervisor_node
from app.config import get_settings
from app.graph.nodes import (
    account_agent_node,
    billing_agent_node,
    classify_request,
    evaluate_resolution,
    general_agent_node,
    generate_response_node,
    human_review,
    load_context,
    save_conversation,
    technical_agent_node,
)
from app.graph.routing import route_after_evaluation, route_after_supervisor
from app.graph.state import SupportState

_checkpointer = None
_compiled = None
_sqlite_conn = None


def build_workflow() -> StateGraph:
    graph = StateGraph(SupportState)

    graph.add_node("load_context", load_context)
    graph.add_node("classify_request", classify_request)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("billing_agent", billing_agent_node)
    graph.add_node("technical_agent", technical_agent_node)
    graph.add_node("account_agent", account_agent_node)
    graph.add_node("general_agent", general_agent_node)
    graph.add_node("evaluate_resolution", evaluate_resolution)
    graph.add_node("human_review", human_review)
    graph.add_node("generate_response", generate_response_node)
    graph.add_node("save_conversation", save_conversation)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "classify_request")
    graph.add_edge("classify_request", "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "billing_agent": "billing_agent",
            "technical_agent": "technical_agent",
            "account_agent": "account_agent",
            "general_agent": "general_agent",
        },
    )
    graph.add_edge("billing_agent", "evaluate_resolution")
    graph.add_edge("technical_agent", "evaluate_resolution")
    graph.add_edge("account_agent", "evaluate_resolution")
    graph.add_edge("general_agent", "evaluate_resolution")
    graph.add_conditional_edges(
        "evaluate_resolution",
        route_after_evaluation,
        {
            "human_review": "human_review",
            "generate_response": "generate_response",
        },
    )
    graph.add_edge("human_review", "generate_response")
    graph.add_edge("generate_response", "save_conversation")
    graph.add_edge("save_conversation", END)

    return graph


async def get_checkpointer():
    """Prefer durable SQLite checkpointer; fall back to in-memory."""
    global _checkpointer, _sqlite_conn
    if _checkpointer is not None:
        return _checkpointer

    settings = get_settings()
    path = Path(settings.checkpoint_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _sqlite_conn = await aiosqlite.connect(str(path))
        saver = AsyncSqliteSaver(_sqlite_conn)
        await saver.setup()
        _checkpointer = saver
    except Exception:
        _checkpointer = MemorySaver()
    return _checkpointer


async def get_compiled_graph():
    global _compiled
    if _compiled is not None:
        return _compiled
    checkpointer = await get_checkpointer()
    _compiled = build_workflow().compile(checkpointer=checkpointer)
    return _compiled


def get_compiled_graph_sync():
    """Compile with in-memory checkpointer for unit tests."""
    return build_workflow().compile(checkpointer=MemorySaver())


def reset_compiled_graph() -> None:
    """Reset cached graph (used by tests)."""
    global _compiled, _checkpointer, _sqlite_conn
    _compiled = None
    _checkpointer = None
    _sqlite_conn = None
