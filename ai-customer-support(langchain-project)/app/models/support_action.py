"""SupportAction ORM model — audit log of agent actions."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SupportAction(Base):
    """Record of an action taken (or prepared) during support resolution."""

    __tablename__ = "support_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="completed", nullable=False
    )  # prepared|completed|cancelled|failed
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    approval_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
