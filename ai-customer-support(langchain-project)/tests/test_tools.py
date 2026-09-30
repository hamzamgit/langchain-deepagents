"""Tool unit tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.knowledge_base import KnowledgeBase
from app.tools.ticket_tools import get_service_status, search_knowledge_base
from app.services import billing_service, approval_service
from pathlib import Path


def test_knowledge_search() -> None:
    root = Path(__file__).resolve().parents[1] / "knowledge"
    kb = KnowledgeBase(root)
    hits = kb.search("PDF upload crash Android")
    assert hits
    assert any("technical" in h.source for h in hits)


def test_search_knowledge_tool() -> None:
    results = search_knowledge_base.invoke({"query": "refund timeline"})
    assert isinstance(results, list)
    assert results


def test_service_status_tool() -> None:
    status = get_service_status.invoke({})
    assert status["api"] == "operational"


@pytest.mark.asyncio
async def test_create_approval(seeded_session: AsyncSession) -> None:
    approval = await approval_service.create_approval(
        seeded_session,
        conversation_id="CONV-test",
        customer_id="CUST-001",
        action_type="refund",
        action_payload={"transaction_id": "TX-1002", "amount": 29.99},
        reason="duplicate",
    )
    assert approval.status == "pending"
    resolved = await approval_service.resolve_approval(
        seeded_session, approval.id, approved=True, reviewer_note="ok"
    )
    assert resolved is not None
    assert resolved.status == "approved"


@pytest.mark.asyncio
async def test_get_transactions(seeded_session: AsyncSession) -> None:
    txns = await billing_service.get_transactions(seeded_session, "CUST-001")
    assert len(txns) >= 2
