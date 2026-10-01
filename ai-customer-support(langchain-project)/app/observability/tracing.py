"""Build LangSmith-friendly run configs and post-run tag enrichment.

Phase 1 goal: every support turn gets a named root run with filterable tags
and metadata, without changing agent/tool behavior.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID

from langchain_core.tracers.context import collect_runs

from app.config import get_settings

logger = logging.getLogger("support.observability")

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


def mask_email(value: str) -> str:
    """Mask an email for trace metadata (keep domain for debugging)."""
    if "@" not in value:
        return value
    local, _, domain = value.partition("@")
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def truncate_for_trace(text: str | None, *, limit: int = 200) -> str:
    """Truncate free-text before putting it in metadata."""
    if not text:
        return ""
    cleaned = _EMAIL_RE.sub(lambda m: mask_email(m.group(0)), text.strip())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def thread_id_for(conversation_id: str) -> str:
    return f"conv:{conversation_id}"


def build_graph_config(
    *,
    conversation_id: str,
    customer_id: str,
    run_name: str = "support_turn",
    message: str | None = None,
    extra_tags: list[str] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a LangGraph/LangChain config with tracing tags + metadata.

    Safe when LangSmith is disabled — extra keys are ignored by the runtime.
    """
    settings = get_settings()
    thread_id = thread_id_for(conversation_id)

    tags = [
        "support_agent",
        f"env:{settings.app_env}",
        f"version:{settings.agent_version}",
        *(extra_tags or []),
    ]

    metadata: dict[str, Any] = {
        "conversation_id": conversation_id,
        "customer_id": customer_id,
        "thread_id": thread_id,
        "llm_model": settings.llm_model,
        "agent_version": settings.agent_version,
        "app_env": settings.app_env,
        "app_name": settings.app_name,
    }
    if message is not None:
        metadata["message_preview"] = truncate_for_trace(message)

    if extra_metadata:
        metadata.update(extra_metadata)

    return {
        "configurable": {"thread_id": thread_id},
        "run_name": run_name,
        "tags": tags,
        "metadata": metadata,
    }


def outcome_tags(
    *,
    assigned_agent: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    requires_human: bool = False,
    approval_id: str | None = None,
    ticket_id: str | None = None,
    errors: list[str] | None = None,
) -> list[str]:
    """Derive filter tags from a completed (or interrupted) turn outcome."""
    tags: list[str] = []
    if assigned_agent:
        tags.append(f"agent:{assigned_agent}")
    if category:
        tags.append(f"category:{category}")
    if priority:
        tags.append(f"priority:{priority}")
    if status:
        tags.append(f"status:{status}")
    if requires_human or status == "awaiting_approval":
        tags.append("hitl")
        tags.append("awaiting_approval")
    if approval_id:
        tags.append("has_approval")
    if ticket_id:
        tags.append("has_ticket")
    if errors:
        tags.append("has_errors")
    return tags


def enrich_run_from_outcome(
    run_id: UUID | str | None,
    *,
    assigned_agent: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    requires_human: bool = False,
    approval_id: str | None = None,
    ticket_id: str | None = None,
    errors: list[str] | None = None,
) -> None:
    """Attach post-run tags/metadata to the LangSmith root run when tracing is on."""
    settings = get_settings()
    if not settings.tracing_enabled or run_id is None:
        return

    # update_run replaces tags — include base tags so filters stay intact
    tags = [
        "support_agent",
        f"env:{settings.app_env}",
        f"version:{settings.agent_version}",
        *outcome_tags(
            assigned_agent=assigned_agent,
            category=category,
            priority=priority,
            status=status,
            requires_human=requires_human,
            approval_id=approval_id,
            ticket_id=ticket_id,
            errors=errors,
        ),
    ]
    extra = {
        "assigned_agent": assigned_agent,
        "category": category,
        "priority": priority,
        "status": status,
        "requires_human": requires_human,
        "approval_id": approval_id,
        "ticket_id": ticket_id,
        "error_count": len(errors or []),
    }

    try:
        from langsmith import Client

        client = Client()
        client.update_run(
            str(run_id),
            tags=tags,
            extra={"metadata": {k: v for k, v in extra.items() if v is not None}},
        )
    except Exception as exc:  # noqa: BLE001 — never break support flow for tracing
        logger.warning("Failed to enrich LangSmith run %s: %s", run_id, exc)


class RunCollector:
    """Collect the root LangSmith/LangChain run id for a single graph invoke.

    Usage::

        with RunCollector() as collector:
            result = await graph.ainvoke(state, config=config)
        enrich_run_from_outcome(collector.run_id, ...)
    """

    def __init__(self) -> None:
        self._cm = collect_runs()
        self._cb: Any = None
        self.run_id: UUID | None = None

    def __enter__(self) -> RunCollector:
        self._cb = self._cm.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        self._cm.__exit__(*args)
        traced = getattr(self._cb, "traced_runs", None) or []
        if traced:
            self.run_id = traced[0].id
