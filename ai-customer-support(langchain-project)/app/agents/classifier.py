"""Intent classification with structured output + heuristic fallback."""

from __future__ import annotations

import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_chat_model, llm_available
from app.prompts import CLASSIFIER_SYSTEM
from app.schemas.support import SupportIntent


def classify_heuristic(message: str) -> SupportIntent:
    """Deterministic classifier for tests / offline demo mode."""
    text = message.lower()

    billing_kw = [
        "charged",
        "charge",
        "refund",
        "invoice",
        "payment",
        "subscription",
        "billing",
        "twice",
        "duplicate",
    ]
    technical_kw = [
        "crash",
        "crashes",
        "bug",
        "error",
        "upload",
        "pdf",
        "api",
        "mobile",
        "app",
        "login problem",
    ]
    account_kw = [
        "password",
        "forgot",
        "email change",
        "change my email",
        "account",
        "delete my account",
        "reset",
    ]
    general_kw = ["hours", "payment method", "how long", "policy", "support hours"]

    def score(keywords: list[str]) -> int:
        return sum(1 for k in keywords if k in text)

    scores = {
        "billing": score(billing_kw),
        "technical": score(technical_kw),
        "account": score(account_kw),
        "general": score(general_kw),
    }

    # Prefer account for password even if "reset" alone is weak
    if "password" in text:
        scores["account"] += 3
    if "charged twice" in text or "duplicate" in text:
        scores["billing"] += 3
    if "pdf" in text and ("crash" in text or "upload" in text):
        scores["technical"] += 3
    if "isn't documented" in text or "not documented" in text or "something that isn't" in text:
        scores["general"] += 3

    category = max(scores, key=lambda k: scores[k])
    if scores[category] == 0:
        category = "general"

    requires_human = bool(
        re.search(r"refund|delete.*(account)|email change|charged twice|duplicate", text)
    )
    priority = "high" if requires_human or "crash" in text else "medium"
    if "critical" in text or "outage" in text:
        priority = "critical"

    return SupportIntent(
        category=category,  # type: ignore[arg-type]
        priority=priority,  # type: ignore[arg-type]
        summary=message.strip()[:200],
        requires_human=requires_human,
        reason=f"Heuristic classification based on keyword scores: {scores}",
    )


async def classify_intent(message: str, *, use_llm: bool | None = None) -> SupportIntent:
    """Classify a support message into a structured SupportIntent."""
    should_use_llm = llm_available() if use_llm is None else use_llm
    if not should_use_llm:
        return classify_heuristic(message)

    llm = get_chat_model().with_structured_output(SupportIntent)
    result = await llm.ainvoke(
        [
            SystemMessage(content=CLASSIFIER_SYSTEM),
            HumanMessage(content=message),
        ]
    )
    if isinstance(result, SupportIntent):
        return result
    return SupportIntent.model_validate(result)
