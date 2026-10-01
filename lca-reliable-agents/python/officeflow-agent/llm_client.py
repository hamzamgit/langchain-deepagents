"""Shared OpenRouter (OpenAI-compatible) client for OfficeFlow agents.

Change models / base URL / key handling here — all agents pick it up.
Override with env vars:
  OPENROUTER_API_KEY          (required)
  OPENROUTER_CHAT_MODEL       (default: openai/gpt-5-nano)
  OPENROUTER_EMBEDDING_MODEL  (default: openai/text-embedding-3-small)
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from langsmith.wrappers import wrap_openai

# Repo root: .../lca-reliable-agents (officeflow-agent -> python -> repo)
_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_REPO_ROOT / ".env")
load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CHAT_MODEL = os.getenv("OPENROUTER_CHAT_MODEL", "openai/gpt-5-nano")
EMBEDDING_MODEL = os.getenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small")

_api_key = os.getenv("OPENROUTER_API_KEY")
if not _api_key:
    raise RuntimeError(
        "OPENROUTER_API_KEY is not set. Add it to your .env file "
        "(get a key at https://openrouter.ai/keys)."
    )

client = wrap_openai(
    AsyncOpenAI(
        api_key=_api_key,
        base_url=OPENROUTER_BASE_URL,
    )
)

__all__ = [
    "client",
    "CHAT_MODEL",
    "EMBEDDING_MODEL",
    "OPENROUTER_BASE_URL",
]
