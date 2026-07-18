"""
Local ReasoningProvider backed by Ollama, running entirely on-machine —
no API key, no network call, no per-request cost. This is the
architecturally "correct" reasoning provider for a project that
otherwise claims to be local-first everywhere else (capture, ML gate,
embeddings) — AnthropicReasoningProvider remains in the codebase as an
alternative implementation (unit-tested via mocks, not live-verified
due to no funded account), but this is the one actually run and
demoed live.

Token usage is estimated (Ollama's response includes eval_count /
prompt_eval_count, which map reasonably to output/input tokens) rather
than exact like the Anthropic SDK's usage field, since Ollama's
tokenizer accounting isn't guaranteed identical to Anthropic's schema —
documented here rather than presented as precisely equivalent.
"""

from __future__ import annotations

import logging

from cogn_os.reasoning.prompts import SUGGESTION_SYSTEM_PROMPT_V1
from cogn_os.reasoning.types import ReasoningProvider, ReasoningRequest, ReasoningResult

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama3.2"


class OllamaReasoningProvider(ReasoningProvider):
    def __init__(self, model: str = DEFAULT_MODEL, host: str = "http://localhost:11434") -> None:
        try:
            import ollama
        except ImportError as e:
            raise RuntimeError("ollama package not installed. pip install ollama") from e

        self._client = ollama.Client(host=host)
        self._model = model

    def get_suggestion(self, request: ReasoningRequest) -> ReasoningResult:
        user_text = (
            f"Recent activity:\n{request.context_summary}\n\n"
            f"Currently: {request.current_app} — {request.current_window_title}\n\n"
            f"What, if anything, should you suggest right now?"
        )
        # Note: local models here are text-only (llama3.2) — screenshots
        # are silently ignored, unlike AnthropicReasoningProvider which
        # supports vision. A vision-capable local model (e.g. llava)
        # could be swapped in later if screenshot context is needed.
        try:
            response = self._client.chat(
                model=self._model,
                messages=[
                    {"role": "system", "content": SUGGESTION_SYSTEM_PROMPT_V1},
                    {"role": "user", "content": user_text},
                ],
            )
            text = response["message"]["content"].strip()
            suggestion = None if text.upper().startswith("NONE") else text

            return ReasoningResult(
                suggestion=suggestion,
                input_tokens=response.get("prompt_eval_count", 0),
                output_tokens=response.get("eval_count", 0),
                model=self._model,
            )
        except Exception:
            logger.exception("ollama call failed; is 'ollama serve' running with model '%s' pulled?", self._model)
            return ReasoningResult(suggestion=None, input_tokens=0, output_tokens=0, model=self._model)