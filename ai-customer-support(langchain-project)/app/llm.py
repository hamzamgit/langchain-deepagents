"""LLM factory — provider-agnostic via OpenAI-compatible API."""

from __future__ import annotations

import os
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import Settings, get_settings


def configure_langsmith(settings: Settings | None = None) -> None:
    """Enable LangSmith tracing when configured; safe no-op otherwise."""
    settings = settings or get_settings()
    if settings.tracing_enabled:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    else:
        os.environ.setdefault("LANGSMITH_TRACING", "false")
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")


@lru_cache
def get_chat_model(
    *,
    temperature: float | None = None,
    model: str | None = None,
) -> ChatOpenAI:
    """Return a ChatOpenAI client pointed at the configured provider."""
    settings = get_settings()
    configure_langsmith(settings)

    kwargs: dict = {
        "model": model or settings.llm_model,
        "temperature": settings.llm_temperature if temperature is None else temperature,
        "api_key": settings.llm_api_key or "missing-key",
    }
    if settings.llm_base_url:
        kwargs["base_url"] = settings.llm_base_url
    return ChatOpenAI(**kwargs)


def llm_available() -> bool:
    """True when a real API key is configured (not placeholder)."""
    key = get_settings().llm_api_key.strip()
    return bool(key) and key not in {"your-api-key-here", "test-key", "missing-key"}
