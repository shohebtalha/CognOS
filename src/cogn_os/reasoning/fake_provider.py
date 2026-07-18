"""
Test double — returns scripted suggestions without any network call.
Every test in this codebase that touches the reasoning layer uses this,
never the real AnthropicReasoningProvider (which is tested separately,
deliberately, against the real API in Commit #5).
"""

from __future__ import annotations

from cogn_os.reasoning.types import ReasoningProvider, ReasoningRequest, ReasoningResult


class FakeReasoningProvider(ReasoningProvider):
    def __init__(self, suggestion: str | None = "Fake suggestion") -> None:
        self._suggestion = suggestion
        self.call_count = 0
        self.received_requests: list[ReasoningRequest] = []

    def get_suggestion(self, request: ReasoningRequest) -> ReasoningResult:
        self.call_count += 1
        self.received_requests.append(request)
        return ReasoningResult(
            suggestion=self._suggestion, input_tokens=10, output_tokens=5, model="fake-model",
        )

    def set_next(self, suggestion: str | None) -> None:
        self._suggestion = suggestion