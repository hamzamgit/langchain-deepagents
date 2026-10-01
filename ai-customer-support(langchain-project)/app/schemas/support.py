"""Pydantic schemas for support intent and agent routing."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class SupportIntent(BaseModel):
    """Structured classification of a customer support request."""

    category: Literal["billing", "technical", "account", "general"]
    priority: Literal["low", "medium", "high", "critical"]
    summary: str = Field(..., description="One-sentence summary of the request")
    requires_human: bool = Field(
        default=False,
        description="Whether this request likely needs a human agent",
    )
    reason: str = Field(..., description="Brief rationale for the classification")


class AgentRouteDecision(BaseModel):
    """Supervisor routing decision."""

    assigned_agent: Literal["billing", "technical", "account", "general"]
    reason: str


class ResolutionDecision(BaseModel):
    """Decision after a specialized agent finishes investigating."""

    resolved: bool
    requires_approval: bool = False
    approval_action_type: Optional[str] = None
    approval_payload: dict[str, Any] = Field(default_factory=dict)
    resolution_summary: str
    customer_response_draft: str
    ticket_id: Optional[str] = None


class TicketCreate(BaseModel):
    customer_id: str
    conversation_id: Optional[str] = None
    category: str
    priority: str = "medium"
    subject: str
    description: str
    created_by_agent: Optional[str] = None


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    conversation_id: Optional[str] = None
    category: str
    priority: str
    status: str
    subject: str
    description: str
    created_by_agent: Optional[str] = None
    created_at: datetime
    updated_at: datetime
