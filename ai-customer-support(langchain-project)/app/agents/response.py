"""Final customer-facing response generation."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.state import SupportState
from app.llm import get_chat_model, llm_available
from app.middleware.logging import log_agent_step
from app.prompts import RESPONSE_SYSTEM


def _draft_from_state(state: SupportState) -> str:
    resolution = state.get("resolution") or {}
    draft = resolution.get("customer_response_draft")
    if draft:
        return str(draft)

    if state.get("requires_human") and state.get("approval_status") == "pending":
        return (
            "I've prepared an action that needs human approval. "
            "A specialist will review it shortly and you'll get a confirmation."
        )
    if state.get("approval_status") == "approved":
        return "Your request was approved and the action has been completed."
    if state.get("approval_status") == "rejected":
        return (
            "A reviewer declined the requested action. "
            "Please reply if you'd like us to explore alternatives."
        )
    return "Thanks for contacting support. We're looking into your request."


async def generate_final_response(state: SupportState) -> dict[str, Any]:
    log_agent_step(
        conversation_id=state.get("conversation_id"),
        agent="response",
        step="generate",
        details={"approval_status": state.get("approval_status")},
    )

    draft = _draft_from_state(state)

    # Optional LLM polish — never invent new facts beyond the draft/context
    if llm_available():
        try:
            llm = get_chat_model(temperature=0.2)
            result = await llm.ainvoke(
                [
                    SystemMessage(content=RESPONSE_SYSTEM),
                    HumanMessage(
                        content=(
                            f"Customer message: {state.get('message')}\n"
                            f"Resolution summary: {(state.get('resolution') or {}).get('resolution_summary')}\n"
                            f"Approval status: {state.get('approval_status')}\n"
                            f"Ticket ID: {state.get('ticket_id')}\n"
                            f"Draft to polish (keep all facts):\n{draft}"
                        )
                    ),
                ]
            )
            content = getattr(result, "content", None)
            if isinstance(content, str) and content.strip():
                draft = content.strip()
        except Exception as exc:  # noqa: BLE001
            errors = list(state.get("errors") or [])
            errors.append(f"response_llm_error: {exc}")
            return {"final_response": draft, "errors": errors}

    return {"final_response": draft}
