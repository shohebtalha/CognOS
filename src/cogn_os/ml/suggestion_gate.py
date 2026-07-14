"""
SuggestionGate decides whether a given event is worth escalating to the
LLM. Same interface-first pattern as everything else in this codebase
(WindowInfoSource, Screenshotter, Clock): the capture loop depends on
this abstraction, never on scikit-learn or a specific model file
directly. This is what lets tests run deterministically without a
trained model on disk, and lets Day 8's retrained model swap in with
zero changes to calling code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cogn_os.ml.features import SuggestionFeatures


class SuggestionGate(ABC):
    @abstractmethod
    def should_flag(self, features: SuggestionFeatures) -> bool:
        """Return True if this event is worth an LLM call."""
        raise NotImplementedError