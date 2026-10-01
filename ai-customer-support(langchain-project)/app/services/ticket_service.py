"""Ticket persistence service."""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket
from app.schemas.support import TicketCreate


def _new_ticket_id() -> str:
    return f"TICKET-{uuid4().hex[:8].upper()}"


async def create_ticket(session: AsyncSession, data: TicketCreate) -> Ticket:
    ticket = Ticket(
        id=_new_ticket_id(),
        customer_id=data.customer_id,
        conversation_id=data.conversation_id,
        category=data.category,
        priority=data.priority,
        subject=data.subject,
        description=data.description,
        created_by_agent=data.created_by_agent,
        status="open",
    )
    session.add(ticket)
    await session.flush()
    return ticket


async def get_ticket(session: AsyncSession, ticket_id: str) -> Ticket | None:
    result = await session.execute(select(Ticket).where(Ticket.id == ticket_id))
    return result.scalar_one_or_none()


async def list_tickets(
    session: AsyncSession,
    *,
    customer_id: str | None = None,
    status: str | None = None,
) -> list[Ticket]:
    stmt = select(Ticket).order_by(Ticket.created_at.desc())
    if customer_id:
        stmt = stmt.where(Ticket.customer_id == customer_id)
    if status:
        stmt = stmt.where(Ticket.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())
