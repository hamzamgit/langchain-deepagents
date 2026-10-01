"""Ticket API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.schemas.support import TicketRead
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("", response_model=list[TicketRead])
async def list_tickets(
    customer_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_db_session),
) -> list[TicketRead]:
    tickets = await ticket_service.list_tickets(
        session, customer_id=customer_id, status=status_filter
    )
    return [TicketRead.model_validate(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketRead)
async def get_ticket(
    ticket_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> TicketRead:
    ticket = await ticket_service.get_ticket(session, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return TicketRead.model_validate(ticket)
