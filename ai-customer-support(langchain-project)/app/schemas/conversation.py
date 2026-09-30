"""Pydantic schemas for conversations and messages."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)
    customer_id: Optional[str] = Field(
        default=None,
        description="Required when creating the first message without an existing conversation",
    )


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    agent_name: Optional[str] = None
    created_at: datetime


class ConversationCreate(BaseModel):
    customer_id: str = Field(..., examples=["CUST-001"])
    initial_message: Optional[str] = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    status: str
    category: Optional[str] = None
    priority: Optional[str] = None
    summary: Optional[str] = None
    assigned_agent: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead] = Field(default_factory=list)


class MessageResponse(BaseModel):
    """Response returned after processing a customer message."""

    conversation_id: str
    message_id: str
    status: str
    category: Optional[str] = None
    priority: Optional[str] = None
    assigned_agent: Optional[str] = None
    requires_human: bool = False
    approval_id: Optional[str] = None
    final_response: Optional[str] = None
    ticket_id: Optional[str] = None
