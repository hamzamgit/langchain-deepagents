"""Shared pytest fixtures — isolated SQLite DB per test."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.main import create_app
from app.models.customer import Customer
from app.models.ticket import Ticket
from app.models.transaction import Transaction


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def _knowledge_dir(monkeypatch):
    root = Path(__file__).resolve().parents[1] / "knowledge"
    monkeypatch.setenv("KNOWLEDGE_DIR", str(root))
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr(get_settings(), "knowledge_dir", str(root))
    from app.tools.knowledge_base import KnowledgeBase
    import app.tools.knowledge_base as kb_mod

    kb_mod._kb = KnowledgeBase(root)


@pytest.fixture(autouse=True)
def _reset_graph():
    from app.graph.workflow import reset_compiled_graph

    reset_compiled_graph()
    yield
    reset_compiled_graph()


@pytest_asyncio.fixture
async def db_engine(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as sess:
        yield sess
        await sess.rollback()


async def _seed(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    session.add_all(
        [
            Customer(
                id="CUST-001",
                email="alice@example.com",
                full_name="Alice Johnson",
                account_status="active",
                plan="pro",
                device="iPhone 15",
                app_version="3.2.1",
            ),
            Customer(
                id="CUST-002",
                email="bob@example.com",
                full_name="Bob Smith",
                account_status="active",
                plan="basic",
                device="Pixel 8",
                app_version="3.2.0",
            ),
            Customer(
                id="CUST-003",
                email="carol@example.com",
                full_name="Carol Lee",
                account_status="active",
                plan="enterprise",
                device="Samsung Galaxy S24",
                app_version="3.1.9",
            ),
        ]
    )
    session.add_all(
        [
            Transaction(
                id="TX-1001",
                customer_id="CUST-001",
                amount=Decimal("29.99"),
                status="succeeded",
                description="Pro Monthly Subscription",
                invoice_id="INV-5001",
                created_at=now - timedelta(days=1, hours=2),
            ),
            Transaction(
                id="TX-1002",
                customer_id="CUST-001",
                amount=Decimal("29.99"),
                status="succeeded",
                description="Pro Monthly Subscription",
                invoice_id="INV-5001",
                created_at=now - timedelta(days=1, hours=1),
            ),
            Transaction(
                id="TX-2001",
                customer_id="CUST-002",
                amount=Decimal("9.99"),
                status="failed",
                description="Basic Monthly Subscription",
                invoice_id="INV-6001",
                created_at=now - timedelta(days=2),
            ),
        ]
    )
    session.add(
        Ticket(
            id="TICKET-1002",
            customer_id="CUST-003",
            category="technical",
            priority="high",
            status="open",
            subject="App crash on PDF upload",
            description="Crash on Android PDF upload",
            created_by_agent="technical",
        )
    )
    await session.commit()


@pytest_asyncio.fixture
async def seeded_session(session: AsyncSession) -> AsyncSession:
    await _seed(session)
    return session


@pytest_asyncio.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def client(db_engine, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    """ASGI test client with DB dependency overridden to the test engine."""
    from app.api import dependencies
    from app.database import session as db_session_module
    from app.tools import _session as tools_session

    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as sess:
            try:
                yield sess
                await sess.commit()
            except Exception:
                await sess.rollback()
                raise

    async with session_factory() as sess:
        await _seed(sess)

    monkeypatch.setattr(db_session_module, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(dependencies, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(tools_session, "AsyncSessionLocal", session_factory)

    # Force in-memory checkpointer for tests
    from langgraph.checkpoint.memory import MemorySaver
    import app.graph.workflow as wf

    monkeypatch.setattr(wf, "_checkpointer", MemorySaver())
    monkeypatch.setattr(wf, "_compiled", None)

    application = create_app()
    application.dependency_overrides[dependencies.get_db_session] = _override_db

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    application.dependency_overrides.clear()
