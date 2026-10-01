"""Approval ORM model for human-in-the-loop."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Approval(Base):
    """Pending or resolved human approval for a sensitive action."""

    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False
    )  # pending|approved|rejected
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    graph_thread_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
