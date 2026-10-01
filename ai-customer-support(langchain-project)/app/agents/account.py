"""Account agent — password reset and sensitive account changes."""

from __future__ import annotations

from typing import Any
import re

from app.graph.state import SupportState
from app.middleware.logging import log_agent_step
from app.tools.account_tools import create_password_reset, get_account_status, prepare_email_change
from app.tools.ticket_tools import search_knowledge_base


async def run_account_agent(state: SupportState) -> dict[str, Any]:
    customer_id = state["customer_id"]
    conversation_id = state["conversation_id"]
    message = state.get("message", "")
    tool_results: list[dict[str, Any]] = list(state.get("tool_results") or [])

    log_agent_step(
        conversation_id=conversation_id,
        agent="account",
        step="investigate",
        details={"message": message[:200]},
    )

    status = await get_account_status.ainvoke({"customer_id": customer_id})
    tool_results.append({"tool": "get_account_status", "result": status})

    kb = search_knowledge_base.invoke({"query": message})
    tool_results.append({"tool": "search_knowledge_base", "result": kb})

    text = message.lower()

    if "password" in text or "forgot" in text:
        reset = await create_password_reset.ainvoke(
            {"customer_id": customer_id, "conversation_id": conversation_id}
        )
        tool_results.append({"tool": "create_password_reset", "result": reset})
        return {
            "tool_results": tool_results,
            "assigned_agent": "account",
            "requires_human": False,
            "resolution": {
                "resolved": True,
                "requires_approval": False,
                "resolution_summary": "Password reset initiated.",
                "customer_response_draft": (
                    f"I've started a password reset for {reset.get('email_hint', 'your email')}. "
                    "Check your inbox (and spam folder) for a link valid for 60 minutes. "
                    "For security, we never share passwords in chat."
                ),
            },
        }

    if "email" in text and ("change" in text or "update" in text):
        match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", message)
        new_email = match.group(0) if match else "new-email@example.com"
        prep = await prepare_email_change.ainvoke(
            {
                "customer_id": customer_id,
                "conversation_id": conversation_id,
                "new_email": new_email,
            }
        )
        tool_results.append({"tool": "prepare_email_change", "result": prep})
        return {
            "tool_results": tool_results,
            "assigned_agent": "account",
            "requires_human": True,
            "approval_id": prep.get("approval_id"),
            "approval_status": "pending",
            "resolution": {
                "resolved": False,
                "requires_approval": True,
                "approval_action_type": "email_change",
                "approval_payload": prep.get("payload", {}),
                "resolution_summary": "Email change awaiting human approval.",
                "customer_response_draft": (
                    f"I've prepared an email change to {new_email}. "
                    "A human reviewer must approve this for security. "
                    "We'll confirm once it's completed."
                ),
            },
        }

    return {
        "tool_results": tool_results,
        "assigned_agent": "account",
        "requires_human": False,
        "resolution": {
            "resolved": True,
            "requires_approval": False,
            "resolution_summary": "Provided account status.",
            "customer_response_draft": (
                f"Your account ({status.get('full_name', customer_id)}) is "
                f"**{status.get('account_status', 'unknown')}** on the "
                f"**{status.get('plan', 'unknown')}** plan. "
                "Tell me if you need a password reset or email change."
            ),
        },
    }
