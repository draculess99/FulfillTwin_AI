from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class Chunk:
    source: str
    section: str
    text: str


class LocalRagEngine:
    """Local TF-IDF RAG over markdown knowledge documents."""

    def __init__(self, knowledge_dir: Path) -> None:
        self.knowledge_dir = knowledge_dir
        self.chunks: list[Chunk] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self.refresh()

    def refresh(self) -> None:
        self.chunks = []
        for path in sorted(self.knowledge_dir.glob("*.md")):
            self.chunks.extend(self._parse_markdown(path))
        if self.chunks:
            self.vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                min_df=1,
            )
            self.matrix = self.vectorizer.fit_transform([c.text for c in self.chunks])
        else:
            self.vectorizer = None
            self.matrix = None

    @staticmethod
    def _parse_markdown(path: Path) -> list[Chunk]:
        text = path.read_text(encoding="utf-8")
        section = "Overview"
        buffer: list[str] = []
        chunks: list[Chunk] = []

        def flush() -> None:
            nonlocal buffer
            body = " ".join(line.strip() for line in buffer if line.strip())
            body = re.sub(r"\s+", " ", body).strip()
            if body:
                chunks.append(Chunk(path.name, section, body))
            buffer = []

        for line in text.splitlines():
            if line.startswith("#"):
                flush()
                section = line.lstrip("#").strip() or "Overview"
            elif not line.strip():
                flush()
            else:
                buffer.append(line)
        flush()
        return chunks

    def search(self, query: str, top_k: int = 4) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query or self.vectorizer is None or self.matrix is None:
            return []
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix).ravel()
        ranked = scores.argsort()[::-1][: max(1, top_k)]
        results: list[dict[str, Any]] = []
        for idx in ranked:
            score = float(scores[idx])
            if score <= 0:
                continue
            chunk = self.chunks[int(idx)]
            results.append(
                {
                    "source": chunk.source,
                    "section": chunk.section,
                    "text": chunk.text,
                    "score": round(score, 4),
                    "citation": f"{chunk.source} — {chunk.section}",
                }
            )
        return results
