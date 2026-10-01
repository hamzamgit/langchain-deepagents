"""Billing tools — controlled access to transactions and refund requests."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.middleware.logging import log_tool_call
from app.services import approval_service, billing_service
from app.tools._session import with_session


@tool
async def get_transactions(customer_id: str) -> list[dict[str, Any]]:
    """Get recent transactions for a customer. Never invent transaction data."""

    async def _run(session):
        with log_tool_call(conversation_id=None, agent="billing", tool="get_transactions"):
            txns = await billing_service.get_transactions(session, customer_id)
            return [
                {
                    "id": t.id,
                    "amount": float(t.amount),
                    "currency": t.currency,
                    "status": t.status,
                    "description": t.description,
                    "invoice_id": t.invoice_id,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in txns
            ]

    return await with_session(_run)


@tool
async def get_invoice(invoice_id: str) -> dict[str, Any]:
    """Get invoice details by invoice ID."""

    async def _run(session):
        with log_tool_call(conversation_id=None, agent="billing", tool="get_invoice"):
            invoice = await billing_service.get_invoice(session, invoice_id)
            if invoice is None:
                return {"error": f"Invoice {invoice_id} not found"}
            return invoice

    return await with_session(_run)


@tool
async def create_refund_request(
    customer_id: str,
    conversation_id: str,
    transaction_id: str,
    amount: float,
    reason: str,
) -> dict[str, Any]:
    """Prepare a refund request that requires human approval. Does NOT execute the refund."""

    async def _run(session):
        with log_tool_call(conversation_id=conversation_id, agent="billing", tool="create_refund_request"):
            txn = await billing_service.get_transaction(session, transaction_id)
            if txn is None:
                return {"error": f"Transaction {transaction_id} not found", "requires_approval": False}
            if txn.customer_id != customer_id:
                return {"error": "Transaction does not belong to this customer", "requires_approval": False}

            payload = {
                "transaction_id": transaction_id,
                "amount": amount,
                "currency": txn.currency,
                "reason": reason,
            }
            approval = await approval_service.create_approval(
                session,
                conversation_id=conversation_id,
                customer_id=customer_id,
                action_type="refund",
                action_payload=payload,
                reason=reason,
            )
            await approval_service.record_support_action(
                session,
                conversation_id=conversation_id,
                customer_id=customer_id,
                agent_name="billing",
                action_type="create_refund_request",
                status="prepared",
                details=payload,
                approval_id=approval.id,
            )
            return {
                "status": "pending_approval",
                "approval_id": approval.id,
                "requires_approval": True,
                "message": "Refund request prepared. Awaiting human approval.",
                "payload": payload,
            }

    return await with_session(_run)
