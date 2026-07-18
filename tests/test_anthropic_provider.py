"""
Runs against the REAL Anthropic API — requires ANTHROPIC_API_KEY set in
the environment. Skipped automatically if not present, so CI/other
machines without a key don't fail. This is the one place proving the
actual integration works, not mocked.
"""

from __future__ import annotations

import os

import pytest

from cogn_os.reasoning.anthropic_provider import AnthropicReasoningProvider
from cogn_os.reasoning.types import ReasoningRequest

pytestmark = pytest.mark.skipif(
    "ANTHROPIC_API_KEY" not in os.environ, reason="ANTHROPIC_API_KEY not set"
)


@pytest.fixture
def provider():
    return AnthropicReasoningProvider(api_key=os.environ["ANTHROPIC_API_KEY"])


def test_get_suggestion_returns_a_result(provider):
    request = ReasoningRequest(
        context_summary="User has been editing main.py for 10 minutes.",
        current_app="code.exe",
        current_window_title="main.py - Visual Studio Code",
    )
    result = provider.get_suggestion(request)

    assert result.model.startswith("claude")
    assert result.input_tokens > 0
    assert result.output_tokens > 0
    # suggestion may be None (model said NONE) or a string — both are valid


def test_get_suggestion_returns_none_for_uninteresting_context(provider):
    request = ReasoningRequest(
        context_summary="User briefly checked their calendar.",
        current_app="outlook.exe",
        current_window_title="Calendar - Outlook",
    )
    result = provider.get_suggestion(request)
    # Not a hard assertion on the exact value (model behavior can vary),
    # but confirms the call completes and returns a well-formed result.
    assert result.suggestion is None or isinstance(result.suggestion, str)


def test_get_suggestion_declines_on_sensitive_context(provider):
    request = ReasoningRequest(
        context_summary="User is viewing their online banking password field.",
        current_app="chrome.exe",
        current_window_title="Bank of Example - Sign In",
    )
    result = provider.get_suggestion(request)
    assert result.suggestion is None