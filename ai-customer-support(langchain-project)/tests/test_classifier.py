"""Classifier and routing unit tests (no live LLM)."""

import pytest

from app.agents.classifier import classify_heuristic, classify_intent
from app.agents.supervisor import route_to_agent
from app.graph.routing import route_after_evaluation, route_after_supervisor
from app.graph.state import SupportState
from app.middleware.safety import is_authorized, is_sensitive_write


@pytest.mark.parametrize(
    "message,category",
    [
        ("I was charged twice for my subscription.", "billing"),
        ("The app crashes when I upload a PDF.", "technical"),
        ("I forgot my password.", "account"),
        ("What are your business hours?", "general"),
        ("I need help with something that isn't documented.", "general"),
    ],
)
def test_heuristic_classifier(message: str, category: str) -> None:
    intent = classify_heuristic(message)
    assert intent.category == category


@pytest.mark.asyncio
async def test_classify_intent_uses_heuristic_without_llm() -> None:
    intent = await classify_intent("I was charged twice.", use_llm=False)
    assert intent.category == "billing"
    assert intent.requires_human is True


def test_supervisor_routing() -> None:
    state: SupportState = {
        "intent": {"category": "billing", "reason": "duplicate charge"},
    }
    decision = route_to_agent(state)
    assert decision.assigned_agent == "billing"
    assert route_after_supervisor({**state, "assigned_agent": "billing"}) == "billing_agent"
    assert route_after_supervisor({**state, "assigned_agent": "technical"}) == "technical_agent"
    assert route_after_supervisor({**state, "assigned_agent": "account"}) == "account_agent"
    assert route_after_supervisor({**state, "assigned_agent": "general"}) == "general_agent"


def test_evaluation_routing() -> None:
    assert (
        route_after_evaluation(
            {"requires_human": True, "approval_id": "APR-1", "approval_status": "pending"}
        )
        == "human_review"
    )
    assert (
        route_after_evaluation({"requires_human": False})
        == "generate_response"
    )
    assert (
        route_after_evaluation(
            {"requires_human": True, "approval_id": "APR-1", "approval_status": "approved"}
        )
        == "generate_response"
    )


def test_tool_authorization() -> None:
    assert is_authorized("get_customer")
    assert is_authorized("create_refund_request", allow_sensitive=True)
    assert not is_authorized("create_refund_request", allow_sensitive=False)
    assert is_sensitive_write("prepare_email_change")
    assert not is_sensitive_write("search_knowledge_base")
