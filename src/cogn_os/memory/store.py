from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from cogn_os.embeddings.types import EmbeddingProvider


@dataclass(frozen=True, slots=True)
class MemoryItem:
    id: str
    text: str
    metadata: dict
    score: float = 0.0


class MemoryStore:
    """Local JSONL + embedding store for small, private semantic memory."""

    def __init__(self, path: Path, embedding_provider: EmbeddingProvider) -> None:
        self._path = path
        self._embedding_provider = embedding_provider
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, item_id: str, text: str, metadata: dict | None = None) -> None:
        vector = self._embedding_provider.embed(text).astype(float).tolist()
        record = {"id": item_id, "text": text, "metadata": metadata or {}, "vector": vector}
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def search(self, query: str, limit: int = 5) -> list[MemoryItem]:
        query_vector = self._embedding_provider.embed(query).astype(float).tolist()
        rows = []
        if not self._path.exists():
            return []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            score = _cosine(query_vector, record["vector"])
            rows.append(MemoryItem(record["id"], record["text"], record["metadata"], score))
        return sorted(rows, key=lambda x: x.score, reverse=True)[:limit]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
