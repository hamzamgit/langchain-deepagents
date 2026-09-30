"""Account agent integration tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.account import run_account_agent
from app.services import conversation_service


@pytest.mark.asyncio
async def test_password_reset_flow(seeded_session: AsyncSession, monkeypatch, db_engine) -> None:
    from app.tools import _session as tools_session
    from app.database import session as db_session_module

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(tools_session, "AsyncSessionLocal", factory)
    monkeypatch.setattr(db_session_module, "AsyncSessionLocal", factory)

    conv = await conversation_service.create_conversation(seeded_session, "CUST-002")
    await seeded_session.commit()

    result = await run_account_agent(
        {
            "customer_id": "CUST-002",
            "conversation_id": conv.id,
            "message": "I forgot my password.",
            "tool_results": [],
        }  # type: ignore[arg-type]
    )
    assert result["assigned_agent"] == "account"
    assert result["requires_human"] is False
    assert result["resolution"]["resolved"] is True
    tools = [t["tool"] for t in result["tool_results"]]
    assert "create_password_reset" in tools
