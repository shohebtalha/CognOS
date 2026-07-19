"""
Tests the full chain: ML gate flags an event -> reasoning provider is
called -> a real suggestion gets persisted. Uses FakeSuggestionGate and
FakeReasoningProvider — no real model, no real API call, deterministic.
"""

from __future__ import annotations

from cogn_os.capture.fake_source import FakeWindowInfoSource
from cogn_os.capture.types import WindowInfo
from cogn_os.config import Settings
from cogn_os.ml.fake_suggestion_gate import FakeSuggestionGate
from cogn_os.reasoning.fake_provider import FakeReasoningProvider
from cogn_os.reasoning.types import ReasoningRequest
from cogn_os.service.clock import FakeClock
from cogn_os.service.wiring import build_ml_gated_loop
from cogn_os.storage.sqlalchemy_repository import (
    SqlAlchemyEventRepository, SqlAlchemySuggestionRepository,
)


def test_flagged_event_triggers_reasoning_call_and_persists_suggestion(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    suggestion_repo = SqlAlchemySuggestionRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, min_seconds_between_llm_calls=0.001)
    gate = FakeSuggestionGate(sequence=True)
    reasoning = FakeReasoningProvider(suggestion="Your test failed on line 12.")

    def on_flagged(info, history):
        request = ReasoningRequest(
            context_summary=f"Recently active: {info.app_name}",
            current_app=info.app_name,
            current_window_title=info.window_title,
        )
        result = reasoning.get_suggestion(request)
        if result.suggestion:
            suggestion_repo.add(info, result.suggestion)

    w1 = WindowInfo.now("code.exe", "main.py")
    loop = build_ml_gated_loop(
        settings, FakeWindowInfoSource([w1]), FakeClock(), event_repo, gate, on_flagged,
    )
    loop.run(max_ticks=1)

    assert reasoning.call_count == 1
    saved = suggestion_repo.recent(limit=10)
    assert len(saved) == 1
    assert saved[0].suggestion == "Your test failed on line 12."


def test_not_flagged_event_never_calls_reasoning_provider(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, min_seconds_between_llm_calls=0.001)
    gate = FakeSuggestionGate(sequence=False)
    reasoning = FakeReasoningProvider()

    def on_flagged(info, history):
        reasoning.get_suggestion(ReasoningRequest(
            context_summary="x", current_app=info.app_name, current_window_title=info.window_title,
        ))

    w1 = WindowInfo.now("code.exe", "main.py")
    loop = build_ml_gated_loop(
        settings, FakeWindowInfoSource([w1]), FakeClock(), event_repo, gate, on_flagged,
    )
    loop.run(max_ticks=1)

    assert reasoning.call_count == 0


def test_model_says_none_does_not_persist_a_suggestion(sqlite_session_factory):
    event_repo = SqlAlchemyEventRepository(sqlite_session_factory)
    suggestion_repo = SqlAlchemySuggestionRepository(sqlite_session_factory)
    settings = Settings(_env_file=None, min_seconds_between_llm_calls=0.001)
    gate = FakeSuggestionGate(sequence=True)
    reasoning = FakeReasoningProvider(suggestion=None)

    def on_flagged(info, history):
        result = reasoning.get_suggestion(ReasoningRequest(
            context_summary="x", current_app=info.app_name, current_window_title=info.window_title,
        ))
        if result.suggestion:
            suggestion_repo.add(info, result.suggestion)

    w1 = WindowInfo.now("code.exe", "main.py")
    loop = build_ml_gated_loop(
        settings, FakeWindowInfoSource([w1]), FakeClock(), event_repo, gate, on_flagged,
    )
    loop.run(max_ticks=1)

    assert reasoning.call_count == 1
    assert suggestion_repo.recent() == []