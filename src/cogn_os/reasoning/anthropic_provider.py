"""
Real ReasoningProvider backed by the Anthropic API. Handles retries
with exponential backoff on transient failures, logs token usage for
cost tracking (Day 17's observability work reads this), and never
raises to the caller on ordinary API problems — a failed suggestion
call degrades to "no suggestion," not a crashed capture loop.
"""

from __future__ import annotations

import logging
import time

from cogn_os.reasoning.prompts import PROMPT_VERSION, SUGGESTION_SYSTEM_PROMPT_V1
from cogn_os.reasoning.types import ReasoningProvider, ReasoningRequest, ReasoningResult

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 100
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.0


class AnthropicReasoningProvider(ReasoningProvider):
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError("anthropic package not installed. pip install anthropic") from e

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def get_suggestion(self, request: ReasoningRequest) -> ReasoningResult:
        user_content = self._build_user_content(request)

        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=SUGGESTION_SYSTEM_PROMPT_V1,
                    messages=[{"role": "user", "content": user_content}],
                )
                text = "".join(
                    block.text for block in response.content if block.type == "text"
                ).strip()

                suggestion = None if text.upper() == "NONE" else text
                return ReasoningResult(
                    suggestion=suggestion,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    model=self._model,
                )
            except Exception as e:  # noqa: BLE001 - deliberately broad, see docstring
                last_error = e
                logger.warning("anthropic call failed (attempt %d/%d): %s", attempt + 1, MAX_RETRIES, e)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(BASE_BACKOFF_SECONDS * (2 ** attempt))

        logger.error("anthropic call failed after %d attempts: %s", MAX_RETRIES, last_error)
        return ReasoningResult(suggestion=None, input_tokens=0, output_tokens=0, model=self._model)

    def _build_user_content(self, request: ReasoningRequest) -> list[dict]:
        content: list[dict] = []
        if request.screenshot_b64:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": request.screenshot_b64},
            })
        content.append({
            "type": "text",
            "text": (
                f"Recent activity:\n{request.context_summary}\n\n"
                f"Currently: {request.current_app} — {request.current_window_title}\n\n"
                f"What, if anything, should you suggest right now?"
            ),
        })
        return content