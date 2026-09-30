"""Conditional routing helpers for the support graph."""

from __future__ import annotations

from typing import Literal

from app.graph.state import SupportState


def route_after_supervisor(
    state: SupportState,
) -> Literal["billing_agent", "technical_agent", "account_agent", "general_agent"]:
    agent = state.get("assigned_agent") or "general"
    mapping = {
        "billing": "billing_agent",
        "technical": "technical_agent",
        "account": "account_agent",
        "general": "general_agent",
    }
    return mapping.get(agent, "general_agent")  # type: ignore[return-value]


def route_after_evaluation(
    state: SupportState,
) -> Literal["human_review", "generate_response"]:
    if state.get("requires_human") and state.get("approval_id"):
        # Only interrupt when approval is still pending
        if state.get("approval_status") in {None, "pending"}:
            return "human_review"
    return "generate_response"
