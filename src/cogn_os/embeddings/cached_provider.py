"""
Wraps any EmbeddingProvider with an in-memory LRU-ish cache keyed on
exact text match. Window titles repeat constantly during normal usage
(same file open for minutes at a time), so this avoids redundant
PyTorch inference calls — a real, measurable performance concern once
this runs continuously in the capture loop (Day 10), not a
micro-optimization for its own sake.
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np

from cogn_os.embeddings.types import EmbeddingProvider


class CachedEmbeddingProvider(EmbeddingProvider):
    def __init__(self, inner: EmbeddingProvider, max_size: int = 500) -> None:
        self._inner = inner
        self._max_size = max_size
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self.cache_hits = 0
        self.cache_misses = 0

    def embed(self, text: str) -> np.ndarray:
        if text in self._cache:
            self.cache_hits += 1
            self._cache.move_to_end(text)  # LRU: mark as recently used
            return self._cache[text]

        self.cache_misses += 1
        vector = self._inner.embed(text)
        self._cache[text] = vector
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)  # evict least-recently-used
        return vector

    @property
    def dimension(self) -> int:
        return self._inner.dimension

    @property
    def hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0