"""Orchestrates running and resuming the support LangGraph workflow."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.workflow import get_compiled_graph
from app.middleware.logging import log_agent_step
from app.services import approval_service, billing_service, conversation_service, customer_service


def thread_id_for(conversation_id: str) -> str:
    return f"conv:{conversation_id}"


async def process_customer_message(
    session: AsyncSession,
    *,
    conversation_id: str,
    customer_id: str,
    message: str,
) -> dict[str, Any]:
    """Run the support graph for a new customer message."""
    graph = await get_compiled_graph()
    thread = {"configurable": {"thread_id": thread_id_for(conversation_id)}}

    initial: dict[str, Any] = {
        "customer_id": customer_id,
        "conversation_id": conversation_id,
        "message": message,
        "tool_results": [],
        "errors": [],
    }

    result = await graph.ainvoke(initial, config=thread)
    interrupted = bool(result.get("__interrupt__"))

    approval_id = result.get("approval_id")
    if interrupted and approval_id:
        approval = await approval_service.get_approval(session, approval_id)
        if approval is not None:
            approval.graph_thread_id = thread_id_for(conversation_id)
            await session.flush()

        draft = (result.get("resolution") or {}).get("customer_response_draft") or (
            "Your request needs human approval before we can proceed."
        )
        # Persist interim agent message while waiting for approval
        await conversation_service.add_message(
            session,
            conversation_id,
            role="agent",
            content=draft,
            agent_name=result.get("assigned_agent"),
        )
        await conversation_service.update_conversation_metadata(
            session,
            conversation_id,
            category=(result.get("intent") or {}).get("category"),
            priority=result.get("priority"),
            summary=(result.get("intent") or {}).get("summary"),
            assigned_agent=result.get("assigned_agent"),
            status="awaiting_approval",
        )

        log_agent_step(
            conversation_id=conversation_id,
            agent="orchestrator",
            step="awaiting_approval",
            details={"approval_id": approval_id},
        )
        return {
            "status": "awaiting_approval",
            "category": (result.get("intent") or {}).get("category"),
            "priority": result.get("priority"),
            "assigned_agent": result.get("assigned_agent"),
            "requires_human": True,
            "approval_id": approval_id,
            "final_response": draft,
            "ticket_id": result.get("ticket_id"),
        }

    return {
        "status": "completed",
        "category": (result.get("intent") or {}).get("category"),
        "priority": result.get("priority"),
        "assigned_agent": result.get("assigned_agent"),
        "requires_human": False,
        "approval_id": result.get("approval_id"),
        "final_response": result.get("final_response"),
        "ticket_id": result.get("ticket_id"),
    }


async def resume_after_approval(
    session: AsyncSession,
    *,
    approval_id: str,
    approved: bool,
    reviewer_note: str | None = None,
) -> dict[str, Any]:
    """Resume an interrupted graph after human decision and execute side effects."""
    approval = await approval_service.get_approval(session, approval_id)
    if approval is None:
        raise ValueError(f"Approval {approval_id} not found")

    if approval.status == "pending":
        approval = await approval_service.resolve_approval(
            session, approval_id, approved=approved, reviewer_note=reviewer_note
        )
        assert approval is not None

    if approved:
        await _execute_approved_action(session, approval)

    # Release DB locks before the graph opens its own tool/save sessions
    await session.commit()

    graph = await get_compiled_graph()
    thread_id = approval.graph_thread_id or thread_id_for(approval.conversation_id)
    thread = {"configurable": {"thread_id": thread_id}}

    snapshot = await graph.aget_state(thread)
    if snapshot.next:
        result = await graph.ainvoke(
            Command(resume={"approved": approved, "reviewer_note": reviewer_note}),
            config=thread,
        )
        final = result.get("final_response")
    else:
        final = None
        result = {}

    if not final:
        if approved:
            final = _fallback_approved_message(approval)
        else:
            final = (
                "A reviewer declined the requested action. "
                "Please reply if you'd like alternatives."
            )
        await conversation_service.add_message(
            session,
            approval.conversation_id,
            role="agent",
            content=final,
            agent_name="human_review",
        )
        await conversation_service.update_conversation_metadata(
            session,
            approval.conversation_id,
            status="open",
        )
        await session.commit()
    elif snapshot.next:
        # Graph save_conversation already persisted the reply; refresh metadata if needed
        pass
    else:
        await conversation_service.update_conversation_metadata(
            session,
            approval.conversation_id,
            status="open",
        )
        await session.commit()

    return {
        "status": "approved" if approved else "rejected",
        "approval_id": approval_id,
        "conversation_id": approval.conversation_id,
        "final_response": final,
    }


def _fallback_approved_message(approval) -> str:
    payload = approval.action_payload or {}
    if approval.action_type == "refund":
        return (
            f"Good news — your refund of ${payload.get('amount')} for transaction "
            f"{payload.get('transaction_id')} has been approved and recorded. "
            "It typically appears on your statement within 5–10 business days."
        )
    if approval.action_type == "email_change":
        return (
            f"Your email change to {payload.get('new_email')} has been approved. "
            "Please use the new address for future logins."
        )
    return "Your request was approved and completed."


async def _execute_approved_action(session: AsyncSession, approval) -> None:
    """Perform the sensitive action only after human approval."""
    payload = approval.action_payload or {}
    if approval.action_type == "refund":
        amount = Decimal(str(payload.get("amount", "0")))
        txn_id = payload.get("transaction_id")
        if txn_id:
            refund = await billing_service.create_refund_record(
                session,
                customer_id=approval.customer_id,
                original_transaction_id=txn_id,
                amount=amount,
                description=f"Refund for {txn_id} (approval {approval.id})",
            )
            await approval_service.record_support_action(
                session,
                conversation_id=approval.conversation_id,
                customer_id=approval.customer_id,
                agent_name="billing",
                action_type="execute_refund",
                status="completed",
                details={"refund_transaction_id": refund.id, **payload},
                approval_id=approval.id,
            )
    elif approval.action_type == "email_change":
        customer = await customer_service.get_customer(session, approval.customer_id)
        new_email = payload.get("new_email")
        if customer and new_email:
            customer.email = new_email
            await session.flush()
            await approval_service.record_support_action(
                session,
                conversation_id=approval.conversation_id,
                customer_id=approval.customer_id,
                agent_name="account",
                action_type="execute_email_change",
                status="completed",
                details=payload,
                approval_id=approval.id,
            )
    else:
        await approval_service.record_support_action(
            session,
            conversation_id=approval.conversation_id,
            customer_id=approval.customer_id,
            agent_name="system",
            action_type=f"execute_{approval.action_type}",
            status="completed",
            details=payload,
            approval_id=approval.id,
        )
