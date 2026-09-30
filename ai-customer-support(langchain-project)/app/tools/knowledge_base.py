"""Simple markdown knowledge-base retrieval (swap-ready for vector search)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings


@dataclass
class KnowledgeHit:
    source: str
    score: float
    excerpt: str


class KnowledgeBase:
    """Keyword-overlap retrieval over Markdown files.

    Intentionally simple so it can be replaced with a vector store later
    without changing tool signatures.
    """

    def __init__(self, knowledge_dir: str | Path | None = None) -> None:
        settings = get_settings()
        self.root = Path(knowledge_dir or settings.knowledge_dir)
        self._docs: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        self._docs = {}
        if not self.root.exists():
            return
        for path in sorted(self.root.glob("*.md")):
            self._docs[path.name] = path.read_text(encoding="utf-8")

    def search(self, query: str, *, top_k: int = 3) -> list[KnowledgeHit]:
        tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9]+", query) if len(t) > 2}
        if not tokens:
            return []

        hits: list[KnowledgeHit] = []
        for name, content in self._docs.items():
            lower = content.lower()
            score = sum(1.0 for t in tokens if t in lower)
            # Boost filename keyword matches
            score += sum(2.0 for t in tokens if t in name.lower())
            if score <= 0:
                continue
            # Prefer a relevant paragraph
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            best = max(
                paragraphs,
                key=lambda p: sum(1 for t in tokens if t in p.lower()),
                default=content[:500],
            )
            hits.append(KnowledgeHit(source=name, score=score, excerpt=best[:800]))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]


_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
