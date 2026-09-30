"""LangGraph node implementations."""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from app.agents.account import run_account_agent
from app.agents.billing import run_billing_agent
from app.agents.classifier import classify_intent
from app.agents.general import run_general_agent
from app.agents.response import generate_final_response
from app.agents.supervisor import supervisor_node
from app.agents.technical import run_technical_agent
from app.graph.state import SupportState
from app.middleware.logging import log_agent_step
from app.services import conversation_service, customer_service
from app.tools._session import with_session

# Re-export for workflow imports
__supervisor__ = supervisor_node


async def load_context(state: SupportState) -> dict[str, Any]:
    """Load customer context and conversation history into state."""
    customer_id = state["customer_id"]
    conversation_id = state["conversation_id"]

    async def _load(session):
        ctx = await customer_service.build_customer_context(session, customer_id)
        history = await conversation_service.get_conversation_history(session, conversation_id)
        return ctx, history

    ctx, history = await with_session(_load)
    log_agent_step(
        conversation_id=conversation_id,
        agent="system",
        step="load_context",
        details={"customer_id": customer_id, "history_len": len(history)},
    )

    if ctx is None:
        return {
            "customer_context": {},
            "conversation_history": history,
            "errors": [f"Customer {customer_id} not found"],
        }

    return {
        "customer_context": ctx.model_dump(),
        "conversation_history": history,
        "errors": [],
    }


async def classify_request(state: SupportState) -> dict[str, Any]:
    message = state.get("message") or ""
    # Include prior customer turns for multi-message context
    history = state.get("conversation_history") or []
    prior = " ".join(m["content"] for m in history if m.get("role") == "customer")
    combined = f"{prior}\n{message}".strip() if prior else message

    intent = await classify_intent(combined)
    log_agent_step(
        conversation_id=state.get("conversation_id"),
        agent="classifier",
        step="classify",
        details=intent.model_dump(),
    )
    return {
        "intent": intent.model_dump(),
        "priority": intent.priority,
        "requires_human": intent.requires_human,
    }


async def billing_agent_node(state: SupportState) -> dict[str, Any]:
    return await run_billing_agent(state)


async def technical_agent_node(state: SupportState) -> dict[str, Any]:
    return await run_technical_agent(state)


async def account_agent_node(state: SupportState) -> dict[str, Any]:
    return await run_account_agent(state)


async def general_agent_node(state: SupportState) -> dict[str, Any]:
    return await run_general_agent(state)


async def evaluate_resolution(state: SupportState) -> dict[str, Any]:
    """Normalize resolution flags before branching to HITL or response."""
    resolution = state.get("resolution") or {}
    requires_human = bool(
        state.get("requires_human") or resolution.get("requires_approval")
    )
    updates: dict[str, Any] = {"requires_human": requires_human}

    # Carry ticket id from resolution if present
    ticket_id = state.get("ticket_id") or resolution.get("ticket_id")
    if ticket_id:
        updates["ticket_id"] = ticket_id

    # If approval already decided (resume path), keep status
    if state.get("approval_status") in {"approved", "rejected"}:
        updates["requires_human"] = False

    log_agent_step(
        conversation_id=state.get("conversation_id"),
        agent="evaluator",
        step="evaluate",
        details={
            "requires_human": updates["requires_human"],
            "approval_id": state.get("approval_id"),
            "approval_status": state.get("approval_status"),
        },
    )
    return updates


async def human_review(state: SupportState) -> dict[str, Any]:
    """Pause the graph until a human approves or rejects the action."""
    payload = {
        "approval_id": state.get("approval_id"),
        "conversation_id": state.get("conversation_id"),
        "customer_id": state.get("customer_id"),
        "action": (state.get("resolution") or {}).get("approval_action_type"),
        "details": (state.get("resolution") or {}).get("approval_payload"),
        "summary": (state.get("resolution") or {}).get("resolution_summary"),
    }
    log_agent_step(
        conversation_id=state.get("conversation_id"),
        agent="human_review",
        step="interrupt",
        details={"approval_id": state.get("approval_id")},
    )
    decision = interrupt(payload)
    # decision expected: {"approved": bool, "reviewer_note": str | None}
    approved = bool(decision.get("approved")) if isinstance(decision, dict) else False
    note = (decision or {}).get("reviewer_note") if isinstance(decision, dict) else None
    if approved:
        draft = _approved_response(state)
    else:
        draft = (
            "A human reviewer declined the requested action. "
            "Please reply if you'd like us to explore alternatives."
        )
        if note:
            draft += f" Note from reviewer: {note}"

    return {
        "approval_status": "approved" if approved else "rejected",
        "requires_human": False,
        "resolution": {
            **(state.get("resolution") or {}),
            "resolved": approved,
            "requires_approval": False,
            "reviewer_note": note,
            "customer_response_draft": draft,
        },
    }


def _approved_response(state: SupportState) -> str:
    action = (state.get("resolution") or {}).get("approval_action_type")
    payload = (state.get("resolution") or {}).get("approval_payload") or {}
    if action == "refund":
        return (
            f"Good news — your refund of ${payload.get('amount')} for transaction "
            f"{payload.get('transaction_id')} has been approved and recorded. "
            "It typically appears on your statement within 5–10 business days."
        )
    if action == "email_change":
        return (
            f"Your email change to {payload.get('new_email')} has been approved "
            "and will be applied shortly. Please use the new address for future logins."
        )
    return "Your request was approved and completed."


async def generate_response_node(state: SupportState) -> dict[str, Any]:
    return await generate_final_response(state)


async def save_conversation(state: SupportState) -> dict[str, Any]:
    """Persist agent reply and conversation metadata."""

    async def _save(session):
        intent = state.get("intent") or {}
        await conversation_service.update_conversation_metadata(
            session,
            state["conversation_id"],
            category=intent.get("category"),
            priority=state.get("priority"),
            summary=intent.get("summary"),
            assigned_agent=state.get("assigned_agent"),
            status=(
                "awaiting_approval"
                if state.get("approval_status") == "pending"
                else "open"
            ),
        )
        final = state.get("final_response")
        if final:
            await conversation_service.add_message(
                session,
                state["conversation_id"],
                role="agent",
                content=final,
                agent_name=state.get("assigned_agent"),
            )

    await with_session(_save)
    log_agent_step(
        conversation_id=state.get("conversation_id"),
        agent="system",
        step="save_conversation",
        details={"has_response": bool(state.get("final_response"))},
    )
    return {}


# Re-export supervisor for workflow wiring
__all__ = [
    "account_agent_node",
    "billing_agent_node",
    "classify_request",
    "evaluate_resolution",
    "general_agent_node",
    "generate_response_node",
    "human_review",
    "load_context",
    "save_conversation",
    "supervisor_node",
    "technical_agent_node",
]
