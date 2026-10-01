"""Technical agent — knowledge-first troubleshooting."""

from __future__ import annotations

from typing import Any

from app.graph.state import SupportState
from app.middleware.logging import log_agent_step
from app.tools.customer_tools import get_customer_device
from app.tools.ticket_tools import create_support_ticket, get_service_status, search_knowledge_base


async def run_technical_agent(state: SupportState) -> dict[str, Any]:
    customer_id = state["customer_id"]
    conversation_id = state["conversation_id"]
    message = state.get("message", "")
    tool_results: list[dict[str, Any]] = list(state.get("tool_results") or [])

    log_agent_step(
        conversation_id=conversation_id,
        agent="technical",
        step="investigate",
        details={"message": message[:200]},
    )

    kb = search_knowledge_base.invoke({"query": message})
    tool_results.append({"tool": "search_knowledge_base", "result": kb})

    status = get_service_status.invoke({})
    tool_results.append({"tool": "get_service_status", "result": status})

    device = await get_customer_device.ainvoke({"customer_id": customer_id})
    tool_results.append({"tool": "get_customer_device", "result": device})

    text = message.lower()
    pdf_crash = "pdf" in text and ("crash" in text or "upload" in text)

    # Known issue match from KB
    known = any(
        isinstance(h, dict) and "pdf" in h.get("excerpt", "").lower()
        for h in (kb or [])
    )

    if pdf_crash and known:
        app_version = (device or {}).get("app_version") or "unknown"
        draft = (
            f"This matches a known Android PDF upload crash. "
            f"Your device is {(device or {}).get('device', 'unknown')} "
            f"on app version {app_version}. "
            "Please update to **3.2.1 or later**, keep PDFs under 10 MB, "
            "and try uploading over Wi‑Fi. "
        )
        # Escalate if already on fixed version
        needs_ticket = False
        try:
            parts = [int(p) for p in str(app_version).split(".")[:3]]
            while len(parts) < 3:
                parts.append(0)
            needs_ticket = tuple(parts) >= (3, 2, 1)
        except ValueError:
            needs_ticket = False

        ticket_id = None
        if needs_ticket:
            ticket = await create_support_ticket.ainvoke(
                {
                    "customer_id": customer_id,
                    "conversation_id": conversation_id,
                    "category": "technical",
                    "subject": "PDF upload crash persists after update",
                    "description": message,
                    "priority": "high",
                    "created_by_agent": "technical",
                }
            )
            tool_results.append({"tool": "create_support_ticket", "result": ticket})
            ticket_id = ticket.get("ticket_id")
            draft += f" Since you're already on {app_version}, I opened ticket {ticket_id}."
        else:
            draft += "If it still crashes after updating, reply here and we'll open a ticket."

        return {
            "tool_results": tool_results,
            "assigned_agent": "technical",
            "ticket_id": ticket_id,
            "requires_human": False,
            "resolution": {
                "resolved": True,
                "requires_approval": False,
                "resolution_summary": "Matched known PDF upload crash guidance.",
                "customer_response_draft": draft,
                "ticket_id": ticket_id,
            },
        }

    # No confident knowledge match → escalate
    ticket = await create_support_ticket.ainvoke(
        {
            "customer_id": customer_id,
            "conversation_id": conversation_id,
            "category": "technical",
            "subject": "Technical issue requiring investigation",
            "description": message,
            "priority": state.get("priority") or "medium",
            "created_by_agent": "technical",
        }
    )
    tool_results.append({"tool": "create_support_ticket", "result": ticket})
    ticket_id = ticket.get("ticket_id")

    return {
        "tool_results": tool_results,
        "assigned_agent": "technical",
        "ticket_id": ticket_id,
        "requires_human": False,
        "resolution": {
            "resolved": True,
            "requires_approval": False,
            "resolution_summary": "No documented fix; ticket created.",
            "customer_response_draft": (
                "I checked our knowledge base and current service status "
                f"({status.get('message', 'unknown')}). I don't have a documented fix "
                f"for this yet, so I created ticket {ticket_id} for our technical team."
            ),
            "ticket_id": ticket_id,
        },
    }
