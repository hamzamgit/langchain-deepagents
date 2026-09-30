"""Supervisor — routes to a specialized agent; does not solve issues."""

from __future__ import annotations

from app.graph.state import SupportState
from app.middleware.logging import log_agent_step
from app.schemas.support import AgentRouteDecision


def route_to_agent(state: SupportState) -> AgentRouteDecision:
    """Map classified intent category to a specialized agent."""
    intent = state.get("intent") or {}
    category = intent.get("category", "general")
    valid = {"billing", "technical", "account", "general"}
    assigned = category if category in valid else "general"
    return AgentRouteDecision(
        assigned_agent=assigned,  # type: ignore[arg-type]
        reason=intent.get("reason") or f"Routed from intent category '{category}'",
    )


async def supervisor_node(state: SupportState) -> dict:
    decision = route_to_agent(state)
    log_agent_step(
        conversation_id=state.get("conversation_id"),
        agent="supervisor",
        step="route",
        details={"assigned_agent": decision.assigned_agent, "reason": decision.reason},
    )
    return {
        "assigned_agent": decision.assigned_agent,
    }
