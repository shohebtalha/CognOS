"""
Test double — returns a scripted boolean (or a fixed value for every
call) instead of running real inference. Mirrors FakeWindowInfoSource,
FakeClock, FakeScreenshotter.
"""

from __future__ import annotations

from collections.abc import Iterable

from cogn_os.ml.features import SuggestionFeatures
from cogn_os.ml.suggestion_gate import SuggestionGate


class FakeSuggestionGate(SuggestionGate):
    def __init__(self, sequence: Iterable[bool] | bool = True) -> None:
        if isinstance(sequence, bool):
            self._fixed = sequence
            self._sequence = None
        else:
            self._fixed = None
            self._sequence = list(sequence)
        self._index = 0
        self.received_features: list[SuggestionFeatures] = []

    def should_flag(self, features: SuggestionFeatures) -> bool:
        self.received_features.append(features)
        if self._fixed is not None:
            return self._fixed
        if self._index >= len(self._sequence):
            return self._sequence[-1] if self._sequence else False
        value = self._sequence[self._index]
        self._index += 1
        return value