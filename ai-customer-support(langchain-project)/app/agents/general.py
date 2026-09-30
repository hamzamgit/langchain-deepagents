"""General agent — knowledge-only answers; escalate when insufficient."""

from __future__ import annotations

from typing import Any

from app.graph.state import SupportState
from app.middleware.logging import log_agent_step
from app.tools.ticket_tools import create_support_ticket, search_knowledge_base


async def run_general_agent(state: SupportState) -> dict[str, Any]:
    customer_id = state["customer_id"]
    conversation_id = state["conversation_id"]
    message = state.get("message", "")
    tool_results: list[dict[str, Any]] = list(state.get("tool_results") or [])

    log_agent_step(
        conversation_id=conversation_id,
        agent="general",
        step="investigate",
        details={"message": message[:200]},
    )

    kb = search_knowledge_base.invoke({"query": message})
    tool_results.append({"tool": "search_knowledge_base", "result": kb})

    text = message.lower()
    insufficient = (
        not kb
        or max((h.get("score", 0) for h in kb), default=0) < 2
        or "isn't documented" in text
        or "not documented" in text
    )

    if insufficient:
        ticket = await create_support_ticket.ainvoke(
            {
                "customer_id": customer_id,
                "conversation_id": conversation_id,
                "category": "general",
                "subject": "Undocumented customer question",
                "description": message,
                "priority": state.get("priority") or "low",
                "created_by_agent": "general",
            }
        )
        tool_results.append({"tool": "create_support_ticket", "result": ticket})
        ticket_id = ticket.get("ticket_id")
        return {
            "tool_results": tool_results,
            "assigned_agent": "general",
            "ticket_id": ticket_id,
            "requires_human": False,
            "resolution": {
                "resolved": True,
                "requires_approval": False,
                "resolution_summary": "Insufficient knowledge; escalated via ticket.",
                "customer_response_draft": (
                    "I searched our knowledge base and don't have enough documented "
                    f"information to answer confidently. I've created ticket {ticket_id} "
                    "so a specialist can follow up."
                ),
                "ticket_id": ticket_id,
            },
        }

    excerpts = "\n\n".join(
        f"From {h['source']}:\n{h['excerpt']}" for h in kb[:2] if isinstance(h, dict)
    )
    return {
        "tool_results": tool_results,
        "assigned_agent": "general",
        "requires_human": False,
        "resolution": {
            "resolved": True,
            "requires_approval": False,
            "resolution_summary": "Answered from knowledge base.",
            "customer_response_draft": (
                "Here's what I found in our documentation:\n\n"
                f"{excerpts}\n\n"
                "If you need more detail, I'm happy to open a ticket."
            ),
        },
    }
