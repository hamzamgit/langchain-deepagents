"""Account tools — password reset and sensitive change preparation."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from langchain_core.tools import tool

from app.middleware.logging import log_tool_call
from app.services import approval_service, customer_service
from app.tools._session import with_session


@tool
async def get_account_status(customer_id: str) -> dict[str, Any]:
    """Get account status and plan for a customer."""

    async def _run(session):
        with log_tool_call(conversation_id=None, agent="account", tool="get_account_status"):
            status = await customer_service.get_account_status(session, customer_id)
            if status is None:
                return {"error": f"Customer {customer_id} not found"}
            return status

    return await with_session(_run)


@tool
async def create_password_reset(customer_id: str, conversation_id: str) -> dict[str, Any]:
    """Initiate a password reset for the email on file. Does not reveal or set a password."""

    async def _run(session):
        with log_tool_call(conversation_id=conversation_id, agent="account", tool="create_password_reset"):
            customer = await customer_service.get_customer(session, customer_id)
            if customer is None:
                return {"error": f"Customer {customer_id} not found"}
            reset_id = f"PWR-{uuid4().hex[:10].upper()}"
            await approval_service.record_support_action(
                session,
                conversation_id=conversation_id,
                customer_id=customer_id,
                agent_name="account",
                action_type="create_password_reset",
                status="completed",
                details={"reset_id": reset_id, "email_hint": _mask_email(customer.email)},
            )
            return {
                "status": "reset_initiated",
                "reset_id": reset_id,
                "email_hint": _mask_email(customer.email),
                "message": "Password reset email sent to the address on file.",
            }

    return await with_session(_run)


@tool
async def prepare_email_change(
    customer_id: str,
    conversation_id: str,
    new_email: str,
) -> dict[str, Any]:
    """Prepare an email change request that requires human approval."""

    async def _run(session):
        with log_tool_call(conversation_id=conversation_id, agent="account", tool="prepare_email_change"):
            customer = await customer_service.get_customer(session, customer_id)
            if customer is None:
                return {"error": f"Customer {customer_id} not found", "requires_approval": False}

            payload = {
                "current_email": customer.email,
                "new_email": new_email,
            }
            approval = await approval_service.create_approval(
                session,
                conversation_id=conversation_id,
                customer_id=customer_id,
                action_type="email_change",
                action_payload=payload,
                reason=f"Customer requested email change to {new_email}",
            )
            await approval_service.record_support_action(
                session,
                conversation_id=conversation_id,
                customer_id=customer_id,
                agent_name="account",
                action_type="prepare_email_change",
                status="prepared",
                details=payload,
                approval_id=approval.id,
            )
            return {
                "status": "pending_approval",
                "approval_id": approval.id,
                "requires_approval": True,
                "message": "Email change prepared. Awaiting human approval.",
                "payload": payload,
            }

    return await with_session(_run)


def _mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    masked = (local[:1] + "***") if local else "***"
    return f"{masked}@{domain}"
