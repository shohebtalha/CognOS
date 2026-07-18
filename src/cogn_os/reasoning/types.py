"""
ReasoningProvider interface — same seam pattern as every external
dependency in this codebase. The capture loop / flagging pipeline
depends on this abstraction, never on the Anthropic SDK directly, so
tests never make real network calls and a different LLM provider could
be swapped in without touching calling code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReasoningRequest:
    """Everything the LLM needs to produce a suggestion (or decline to)."""
    context_summary: str          # recent activity, built by Day 13's context builder
    current_app: str
    current_window_title: str
    screenshot_b64: str | None = None


@dataclass(frozen=True, slots=True)
class ReasoningResult:
    suggestion: str | None        # None means "nothing useful to say"
    input_tokens: int
    output_tokens: int
    model: str


class ReasoningProvider(ABC):
    @abstractmethod
    def get_suggestion(self, request: ReasoningRequest) -> ReasoningResult:
        """Ask the LLM whether there's a useful suggestion for this
        moment. Implementations must never raise on ordinary API
        failures — return a ReasoningResult with suggestion=None instead,
        so callers don't need try/except around every call site."""
        raise NotImplementedError