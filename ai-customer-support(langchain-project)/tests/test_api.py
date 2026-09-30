"""Phase 1+ API and end-to-end scenario tests."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import billing_service, conversation_service, customer_service
from app.services.billing_service import find_duplicate_charges


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_list_customers(client: AsyncClient) -> None:
    response = await client.get("/api/v1/customers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(c["id"] == "CUST-001" for c in data)


@pytest.mark.asyncio
async def test_create_conversation_and_message(client: AsyncClient) -> None:
    create = await client.post(
        "/api/v1/conversations",
        json={"customer_id": "CUST-001"},
    )
    assert create.status_code == 201
    conversation = create.json()
    assert conversation["customer_id"] == "CUST-001"

    msg = await client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"content": "What payment methods do you support?"},
    )
    assert msg.status_code == 201
    body = msg.json()
    assert body["conversation_id"] == conversation["id"]
    assert body["final_response"]
    assert body["assigned_agent"] in {"general", "billing"}


@pytest.mark.asyncio
async def test_billing_scenario_with_approval(client: AsyncClient) -> None:
    create = await client.post(
        "/api/v1/conversations",
        json={"customer_id": "CUST-001"},
    )
    conv_id = create.json()["id"]

    msg = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "I was charged twice for my subscription."},
    )
    assert msg.status_code == 201
    body = msg.json()
    assert body["assigned_agent"] == "billing"
    assert body["requires_human"] is True
    assert body["approval_id"]
    assert body["status"] == "awaiting_approval"

    approvals = await client.get("/api/v1/approvals")
    assert approvals.status_code == 200
    pending = approvals.json()
    assert any(a["id"] == body["approval_id"] for a in pending)

    approve = await client.post(
        f"/api/v1/approvals/{body['approval_id']}/approve",
        json={"reviewer_note": "Verified duplicate"},
    )
    assert approve.status_code == 200
    approved = approve.json()
    assert approved["status"] == "approved"
    assert approved["final_response"]
    assert "refund" in approved["final_response"].lower() or "approved" in approved["final_response"].lower()


@pytest.mark.asyncio
async def test_password_scenario(client: AsyncClient) -> None:
    create = await client.post(
        "/api/v1/conversations",
        json={"customer_id": "CUST-002"},
    )
    conv_id = create.json()["id"]
    msg = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "I forgot my password."},
    )
    assert msg.status_code == 201
    body = msg.json()
    assert body["assigned_agent"] == "account"
    assert body["requires_human"] is False
    assert "password" in (body["final_response"] or "").lower()


@pytest.mark.asyncio
async def test_technical_scenario(client: AsyncClient) -> None:
    create = await client.post(
        "/api/v1/conversations",
        json={"customer_id": "CUST-003"},
    )
    conv_id = create.json()["id"]
    msg = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "The app crashes when I upload a PDF."},
    )
    assert msg.status_code == 201
    body = msg.json()
    assert body["assigned_agent"] == "technical"
    assert body["final_response"]
    assert "pdf" in body["final_response"].lower() or "3.2.1" in body["final_response"]


@pytest.mark.asyncio
async def test_unknown_scenario_creates_ticket(client: AsyncClient) -> None:
    create = await client.post(
        "/api/v1/conversations",
        json={"customer_id": "CUST-001"},
    )
    conv_id = create.json()["id"]
    msg = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "I need help with something that isn't documented."},
    )
    assert msg.status_code == 201
    body = msg.json()
    assert body["assigned_agent"] == "general"
    assert body.get("ticket_id")

    tickets = await client.get("/api/v1/tickets")
    assert tickets.status_code == 200
    assert any(t["id"] == body["ticket_id"] for t in tickets.json())


@pytest.mark.asyncio
async def test_customer_context(seeded_session: AsyncSession) -> None:
    ctx = await customer_service.build_customer_context(seeded_session, "CUST-001")
    assert ctx is not None
    assert ctx.customer_id == "CUST-001"
    assert "TX-1001" in ctx.recent_transaction_ids


@pytest.mark.asyncio
async def test_duplicate_charge_detection(seeded_session: AsyncSession) -> None:
    txns = await billing_service.get_transactions(seeded_session, "CUST-001")
    duplicates = find_duplicate_charges(txns)
    assert len(duplicates) == 1
    assert set(duplicates[0]["transaction_ids"]) == {"TX-1001", "TX-1002"}


@pytest.mark.asyncio
async def test_conversation_history(seeded_session: AsyncSession) -> None:
    conv = await conversation_service.create_conversation(seeded_session, "CUST-001")
    await conversation_service.add_message(
        seeded_session, conv.id, role="customer", content="Hi"
    )
    await conversation_service.add_message(
        seeded_session, conv.id, role="agent", content="How can I help?"
    )
    history = await conversation_service.get_conversation_history(seeded_session, conv.id)
    assert len(history) == 2
    assert history[0]["role"] == "customer"
