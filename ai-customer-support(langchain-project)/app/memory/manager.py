"""Conversation memory helpers."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import conversation_service, customer_service
from app.schemas.customer import CustomerContext


class MemoryManager:
    """Two-level memory: conversation turns + durable customer context."""

    async def get_conversation_memory(
        self, session: AsyncSession, conversation_id: str
    ) -> list[dict[str, str]]:
        return await conversation_service.get_conversation_history(session, conversation_id)

    async def get_customer_memory(
        self, session: AsyncSession, customer_id: str
    ) -> CustomerContext | None:
        return await customer_service.build_customer_context(session, customer_id)

    async def build_agent_context(
        self,
        session: AsyncSession,
        *,
        customer_id: str,
        conversation_id: str,
    ) -> dict[str, Any]:
        history = await self.get_conversation_memory(session, conversation_id)
        customer = await self.get_customer_memory(session, customer_id)
        return {
            "conversation_history": history,
            "customer_context": customer.model_dump() if customer else {},
        }


memory_manager = MemoryManager()
