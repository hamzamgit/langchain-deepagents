"""Approval persistence and decision service."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.support_action import SupportAction


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


async def create_approval(
    session: AsyncSession,
    *,
    conversation_id: str,
    customer_id: str,
    action_type: str,
    action_payload: dict[str, Any],
    reason: str,
    graph_thread_id: str | None = None,
) -> Approval:
    approval = Approval(
        id=_new_id("APR"),
        conversation_id=conversation_id,
        customer_id=customer_id,
        action_type=action_type,
        action_payload=action_payload,
        status="pending",
        reason=reason,
        graph_thread_id=graph_thread_id,
    )
    session.add(approval)
    await session.flush()
    return approval


async def get_approval(session: AsyncSession, approval_id: str) -> Approval | None:
    result = await session.execute(select(Approval).where(Approval.id == approval_id))
    return result.scalar_one_or_none()


async def list_approvals(
    session: AsyncSession,
    *,
    status: str | None = "pending",
) -> list[Approval]:
    stmt = select(Approval).order_by(Approval.created_at.desc())
    if status:
        stmt = stmt.where(Approval.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def resolve_approval(
    session: AsyncSession,
    approval_id: str,
    *,
    approved: bool,
    reviewer_note: str | None = None,
) -> Approval | None:
    approval = await get_approval(session, approval_id)
    if approval is None:
        return None
    if approval.status != "pending":
        raise ValueError(f"Approval {approval_id} is already {approval.status}")

    approval.status = "approved" if approved else "rejected"
    approval.reviewer_note = reviewer_note
    approval.resolved_at = datetime.now(UTC)
    await session.flush()
    return approval


async def record_support_action(
    session: AsyncSession,
    *,
    conversation_id: str,
    customer_id: str,
    agent_name: str,
    action_type: str,
    status: str,
    details: dict[str, Any] | None = None,
    approval_id: str | None = None,
    error_message: str | None = None,
) -> SupportAction:
    action = SupportAction(
        id=_new_id("ACT"),
        conversation_id=conversation_id,
        customer_id=customer_id,
        agent_name=agent_name,
        action_type=action_type,
        status=status,
        details=details or {},
        approval_id=approval_id,
        error_message=error_message,
    )
    session.add(action)
    await session.flush()
    return action
