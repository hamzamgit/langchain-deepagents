"""Conversation API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.schemas.conversation import (
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageResponse,
)
from app.services import conversation_service, customer_service
from app.services import support_orchestrator

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    session: AsyncSession = Depends(get_db_session),
) -> ConversationRead:
    customer = await customer_service.get_customer(session, body.customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    conversation = await conversation_service.create_conversation(session, body.customer_id)
    await session.commit()

    if body.initial_message:
        await conversation_service.add_message(
            session,
            conversation.id,
            role="customer",
            content=body.initial_message,
        )
        await session.commit()
        await support_orchestrator.process_customer_message(
            session,
            conversation_id=conversation.id,
            customer_id=body.customer_id,
            message=body.initial_message,
        )

    conversation = await conversation_service.get_conversation(session, conversation.id)
    assert conversation is not None
    return ConversationRead.model_validate(conversation)


@router.get("/{conversation_id}", response_model=ConversationRead)
async def get_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ConversationRead:
    conversation = await conversation_service.get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return ConversationRead.model_validate(conversation)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: str,
    body: MessageCreate,
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    conversation = await conversation_service.get_conversation(session, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    message = await conversation_service.add_message(
        session,
        conversation_id,
        role="customer",
        content=body.content,
    )
    # Commit so graph tool sessions can see the new message / conversation
    await session.commit()

    outcome = await support_orchestrator.process_customer_message(
        session,
        conversation_id=conversation_id,
        customer_id=conversation.customer_id,
        message=body.content,
    )

    return MessageResponse(
        conversation_id=conversation_id,
        message_id=message.id,
        status=outcome["status"],
        category=outcome.get("category"),
        priority=outcome.get("priority"),
        assigned_agent=outcome.get("assigned_agent"),
        requires_human=outcome.get("requires_human", False),
        approval_id=outcome.get("approval_id"),
        final_response=outcome.get("final_response"),
        ticket_id=outcome.get("ticket_id"),
    )
