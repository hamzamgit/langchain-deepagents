"""Unit tests for LangSmith observability helpers (no network)."""

from __future__ import annotations

from app.observability.tracing import (
    build_graph_config,
    mask_email,
    outcome_tags,
    truncate_for_trace,
)


def test_mask_email() -> None:
    assert mask_email("alice@example.com") == "a***@example.com"
    assert mask_email("not-an-email") == "not-an-email"


def test_truncate_for_trace_masks_email_and_limits_length() -> None:
    text = "Please email me at alice@example.com " + ("x" * 300)
    preview = truncate_for_trace(text, limit=80)
    assert "alice@example.com" not in preview
    assert "a***@example.com" in preview
    assert len(preview) <= 80


def test_build_graph_config_has_run_name_tags_metadata(monkeypatch) -> None:
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AGENT_VERSION", "v1")
    get_settings.cache_clear()

    config = build_graph_config(
        conversation_id="conv-123",
        customer_id="CUST-001",
        message="I was charged twice. Contact alice@example.com",
    )

    assert config["run_name"] == "support_turn"
    assert config["configurable"]["thread_id"] == "conv:conv-123"
    assert "support_agent" in config["tags"]
    assert "env:test" in config["tags"]
    assert "version:v1" in config["tags"]
    assert config["metadata"]["customer_id"] == "CUST-001"
    assert config["metadata"]["conversation_id"] == "conv-123"
    assert "alice@example.com" not in config["metadata"]["message_preview"]
    get_settings.cache_clear()


def test_outcome_tags_for_hitl_billing() -> None:
    tags = outcome_tags(
        assigned_agent="billing",
        category="billing",
        priority="high",
        status="awaiting_approval",
        requires_human=True,
        approval_id="appr-1",
    )
    assert "agent:billing" in tags
    assert "category:billing" in tags
    assert "hitl" in tags
    assert "awaiting_approval" in tags
    assert "has_approval" in tags


def test_enrich_run_noop_without_tracing(monkeypatch) -> None:
    from app.config import get_settings
    from app.observability.tracing import enrich_run_from_outcome

    get_settings.cache_clear()
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGSMITH_API_KEY", "")
    get_settings.cache_clear()

    # Must not raise even with a fake run id
    enrich_run_from_outcome("00000000-0000-0000-0000-000000000000", status="completed")
    get_settings.cache_clear()
