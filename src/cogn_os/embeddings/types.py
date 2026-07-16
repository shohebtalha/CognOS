"""
EmbeddingProvider interface. Same pattern as every other external
dependency in this codebase (WindowInfoSource, Screenshotter,
SuggestionGate): the rest of the app depends on this abstraction, never
on sentence-transformers or torch directly. This is what lets tests run
in milliseconds with a fake fixed-vector provider instead of loading an
actual ~90MB model on every test run.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """Return a 1D float32 embedding vector for the given text."""
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """The fixed length of vectors this provider returns."""
        raise NotImplementedError