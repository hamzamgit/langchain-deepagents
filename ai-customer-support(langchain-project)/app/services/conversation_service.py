"""Conversation and message persistence service."""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.message import Message


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


async def create_conversation(
    session: AsyncSession,
    customer_id: str,
    *,
    status: str = "open",
) -> Conversation:
    conversation = Conversation(
        id=_new_id("CONV"),
        customer_id=customer_id,
        status=status,
    )
    session.add(conversation)
    await session.flush()
    return conversation


async def get_conversation(
    session: AsyncSession, conversation_id: str
) -> Conversation | None:
    result = await session.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    return result.scalar_one_or_none()


async def add_message(
    session: AsyncSession,
    conversation_id: str,
    *,
    role: str,
    content: str,
    agent_name: str | None = None,
) -> Message:
    message = Message(
        id=_new_id("MSG"),
        conversation_id=conversation_id,
        role=role,
        content=content,
        agent_name=agent_name,
    )
    session.add(message)
    await session.flush()
    return message


async def update_conversation_metadata(
    session: AsyncSession,
    conversation_id: str,
    *,
    category: str | None = None,
    priority: str | None = None,
    summary: str | None = None,
    assigned_agent: str | None = None,
    status: str | None = None,
) -> Conversation | None:
    conversation = await get_conversation(session, conversation_id)
    if conversation is None:
        return None
    if category is not None:
        conversation.category = category
    if priority is not None:
        conversation.priority = priority
    if summary is not None:
        conversation.summary = summary
    if assigned_agent is not None:
        conversation.assigned_agent = assigned_agent
    if status is not None:
        conversation.status = status
    await session.flush()
    return conversation


async def get_conversation_history(
    session: AsyncSession, conversation_id: str
) -> list[dict[str, str]]:
    """Return message history as simple role/content dicts for agent memory."""
    conversation = await get_conversation(session, conversation_id)
    if conversation is None:
        return []
    return [{"role": m.role, "content": m.content} for m in conversation.messages]
