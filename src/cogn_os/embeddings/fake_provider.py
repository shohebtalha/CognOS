"""
Test double — returns deterministic fixed vectors based on a simple
hash of the input text, so the same text always produces the same fake
vector across calls without loading any real model. Used everywhere in
tests except the one file (Commit #5) that deliberately tests against
the real model to prove the integration genuinely works.
"""

from __future__ import annotations

import hashlib

import numpy as np

from cogn_os.embeddings.types import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimension: int = 8) -> None:
        self._dimension = dimension
        self.call_count = 0
        self.received_texts: list[str] = []

    def embed(self, text: str) -> np.ndarray:
        self.call_count += 1
        self.received_texts.append(text)
        # Deterministic pseudo-random vector seeded from a hash of the
        # text — same text always yields the same vector, different
        # text yields a different one, without any real model.
        seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        vector = rng.random(self._dimension).astype(np.float32)
        return vector

    @property
    def dimension(self) -> int:
        return self._dimension