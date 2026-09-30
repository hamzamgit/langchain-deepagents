"""Customer ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.ticket import Ticket
    from app.models.transaction import Transaction


class Customer(Base):
    """Customer account used for demo support scenarios."""

    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    plan: Mapped[str] = mapped_column(String(64), default="pro", nullable=False)
    device: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    app_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
