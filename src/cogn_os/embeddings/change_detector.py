"""
Detects whether a new window title represents a *meaningfully* different
context from the previous one, using embedding cosine similarity instead
of exact string equality. Motivation: Day 3's CaptureLoop treats any
title change as a "change" — but "main.py - line 42" -> "main.py - line
43" (same file, cursor moved) is a trivial string diff that shouldn't
re-trigger the ML gate/feature extraction pipeline, while "main.py" ->
"Stack Overflow - segfault error" is a real context switch despite both
being short strings. Cosine similarity on semantic embeddings captures
this distinction; exact string matching cannot.

is_semantically_different() returns True (i.e. "this is a real change")
when similarity is BELOW the threshold — low similarity = different
meaning. This is the inverse framing from a naive "similarity == same"
intuition, documented here explicitly since it's a common source of
off-by-inversion bugs.
"""

from __future__ import annotations

from dataclasses import dataclass

from cogn_os.embeddings.similarity import cosine_similarity
from cogn_os.embeddings.types import EmbeddingProvider

DEFAULT_SIMILARITY_THRESHOLD = 0.75


@dataclass(frozen=True)
class ChangeDecision:
    is_different: bool
    similarity: float
    threshold: float


class SemanticChangeDetector:
    def __init__(
        self, provider: EmbeddingProvider, threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    ) -> None:
        self._provider = provider
        self._threshold = threshold

    def compare(self, previous_title: str | None, current_title: str) -> ChangeDecision:
        if previous_title is None:
            # Nothing to compare against — first-ever title is always
            # treated as a genuine change, same convention as
            # CaptureLoop's existing "no last_seen yet" behavior.
            return ChangeDecision(is_different=True, similarity=0.0, threshold=self._threshold)

        if previous_title == current_title:
            # Exact match short-circuits without running the model —
            # a cheap, correct optimization (identical strings are
            # trivially similarity=1.0, no need to embed either one).
            return ChangeDecision(is_different=False, similarity=1.0, threshold=self._threshold)

        v_prev = self._provider.embed(previous_title)
        v_curr = self._provider.embed(current_title)
        similarity = cosine_similarity(v_prev, v_curr)

        is_different = similarity < self._threshold
        return ChangeDecision(is_different=is_different, similarity=similarity, threshold=self._threshold)