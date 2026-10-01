"""Pydantic schemas for human approvals."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    customer_id: str
    action_type: str
    action_payload: dict[str, Any]
    status: str
    reason: str
    reviewer_note: Optional[str] = None
    graph_thread_id: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class ApprovalDecisionRequest(BaseModel):
    reviewer_note: Optional[str] = Field(default=None, max_length=2000)


class ApprovalDecisionResponse(BaseModel):
    approval_id: str
    status: str
    final_response: Optional[str] = None
    conversation_id: str
