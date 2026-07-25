from __future__ import annotations

from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

from cogn_os.memory.store import MemoryStore, MemoryItem


class RagPipeline:
    def __init__(self, memory: MemoryStore, chunk_chars: int = 1200) -> None:
        self._memory = memory
        self._chunk_chars = chunk_chars

    def ingest_text_file(self, path: Path) -> int:
        text = path.read_text(encoding="utf-8", errors="ignore")
        count = 0
        for index in range(0, len(text), self._chunk_chars):
            chunk = text[index:index + self._chunk_chars].strip()
            if not chunk:
                continue
            item_id = str(uuid5(NAMESPACE_URL, f"{path.resolve()}:{index}"))
            self._memory.add(item_id, chunk, {"path": str(path), "offset": index})
            count += 1
        return count

    def retrieve(self, question: str, limit: int = 5) -> list[MemoryItem]:
        return self._memory.search(question, limit=limit)
