"""Pydantic schemas for customers."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CustomerBase(BaseModel):
    email: str
    full_name: str
    account_status: str = "active"
    plan: str = "pro"
    device: Optional[str] = None
    app_version: Optional[str] = None
    notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    id: str = Field(..., examples=["CUST-001"])


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class CustomerContext(BaseModel):
    """Lightweight context injected into the agent graph state."""

    customer_id: str
    email: str
    full_name: str
    account_status: str
    plan: str
    device: Optional[str] = None
    app_version: Optional[str] = None
    recent_ticket_ids: list[str] = Field(default_factory=list)
    recent_transaction_ids: list[str] = Field(default_factory=list)
