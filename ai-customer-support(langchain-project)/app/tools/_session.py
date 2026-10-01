"""Shared async DB helper for tools (short-lived sessions)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal

T = TypeVar("T")


async def with_session(fn: Callable[[AsyncSession], Awaitable[T]]) -> T:
    async with AsyncSessionLocal() as session:
        try:
            result = await fn(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
