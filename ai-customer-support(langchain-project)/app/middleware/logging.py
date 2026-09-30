"""Structured logging for agent / tool execution (no secrets)."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger("support.agent")

_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "password",
        "token",
        "secret",
        "authorization",
        "llm_api_key",
        "langsmith_api_key",
    }
)


def sanitize(data: Any) -> Any:
    """Redact sensitive keys from nested dicts before logging."""
    if isinstance(data, dict):
        return {
            k: ("***REDACTED***" if k.lower() in _SENSITIVE_KEYS else sanitize(v))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [sanitize(x) for x in data]
    return data


@contextmanager
def log_tool_call(
    *,
    conversation_id: str | None,
    agent: str,
    tool: str,
) -> Iterator[dict[str, Any]]:
    """Context manager that logs tool timing and success/failure."""
    meta: dict[str, Any] = {"success": True, "error": None}
    start = time.perf_counter()
    try:
        yield meta
    except Exception as exc:  # noqa: BLE001 — logged then re-raised
        meta["success"] = False
        meta["error"] = str(exc)
        raise
    finally:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "tool_call conversation_id=%s agent=%s tool=%s elapsed_ms=%s success=%s error=%s",
            conversation_id,
            agent,
            tool,
            elapsed_ms,
            meta["success"],
            meta["error"],
        )


def log_agent_step(
    *,
    conversation_id: str | None,
    agent: str,
    step: str,
    details: dict[str, Any] | None = None,
) -> None:
    logger.info(
        "agent_step conversation_id=%s agent=%s step=%s details=%s",
        conversation_id,
        agent,
        step,
        sanitize(details or {}),
    )
