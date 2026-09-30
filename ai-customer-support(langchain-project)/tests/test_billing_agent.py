"""Billing agent integration tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.billing import run_billing_agent
from app.services import conversation_service


@pytest.mark.asyncio
async def test_billing_duplicate_charge_flow(seeded_session: AsyncSession, monkeypatch, db_engine) -> None:
    from app.tools import _session as tools_session
    from app.database import session as db_session_module

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(tools_session, "AsyncSessionLocal", factory)
    monkeypatch.setattr(db_session_module, "AsyncSessionLocal", factory)

    conv = await conversation_service.create_conversation(seeded_session, "CUST-001")
    await seeded_session.commit()

    state = {
        "customer_id": "CUST-001",
        "conversation_id": conv.id,
        "message": "I was charged twice for my subscription.",
        "tool_results": [],
    }
    result = await run_billing_agent(state)  # type: ignore[arg-type]
    assert result["assigned_agent"] == "billing"
    assert result["requires_human"] is True
    assert result.get("approval_id")
    assert result["resolution"]["requires_approval"] is True
    tools = [t["tool"] for t in result["tool_results"]]
    assert "get_transactions" in tools
    assert "create_refund_request" in tools
