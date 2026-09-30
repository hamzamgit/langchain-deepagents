"""Ticket and knowledge tools."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.middleware.logging import log_tool_call
from app.schemas.support import TicketCreate
from app.services import ticket_service
from app.tools._session import with_session
from app.tools.knowledge_base import get_knowledge_base


@tool
async def create_support_ticket(
    customer_id: str,
    conversation_id: str,
    category: str,
    subject: str,
    description: str,
    priority: str = "medium",
    created_by_agent: str = "general",
) -> dict[str, Any]:
    """Create a support ticket when the issue cannot be resolved automatically."""

    async def _run(session):
        with log_tool_call(conversation_id=conversation_id, agent=created_by_agent, tool="create_support_ticket"):
            ticket = await ticket_service.create_ticket(
                session,
                TicketCreate(
                    customer_id=customer_id,
                    conversation_id=conversation_id,
                    category=category,
                    priority=priority,
                    subject=subject,
                    description=description,
                    created_by_agent=created_by_agent,
                ),
            )
            return {
                "ticket_id": ticket.id,
                "status": ticket.status,
                "subject": ticket.subject,
                "message": f"Support ticket {ticket.id} created.",
            }

    return await with_session(_run)


@tool
def search_knowledge_base(query: str) -> list[dict[str, Any]]:
    """Search company knowledge articles. Do not invent policies not found here."""
    with log_tool_call(conversation_id=None, agent="shared", tool="search_knowledge_base"):
        hits = get_knowledge_base().search(query)
        return [
            {"source": h.source, "score": h.score, "excerpt": h.excerpt}
            for h in hits
        ]


@tool
def get_service_status() -> dict[str, Any]:
    """Get current demo service status (mock)."""
    with log_tool_call(conversation_id=None, agent="technical", tool="get_service_status"):
        return {
            "api": "operational",
            "mobile_app": "operational",
            "billing": "operational",
            "known_incidents": [],
            "message": "All systems operational (demo status).",
        }
