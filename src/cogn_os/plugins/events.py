"""
ContextEvent is the universal event shape every plugin emits, whether
it's an in-process Python observer (OCR, clipboard) or an external
companion extension (browser, VS Code) sending events over HTTP. This
is the single contract that makes "one AI for the OS" architecturally
real: the reasoning engine consumes ContextEvents and never needs to
know which plugin or category produced them.

Design decisions, stated explicitly:

- `source` identifies the plugin (e.g. "window_tracker", "ocr",
  "clipboard", "browser_extension", "vscode_extension") for
  provenance/debugging and for privacy-filter routing (some sources
  may warrant stricter filtering than others).
- `event_type` is a free-text-but-conventioned string (not an enum)
  because the plugin set is intentionally open-ended and unbounded —
  a closed enum would need editing every time a new plugin is added,
  defeating the extensibility goal. Known conventions are documented
  in EVENT_TYPE_CONVENTIONS below; plugins should use those where
  applicable rather than inventing synonyms.
- `payload` is a flat dict, not a nested/typed structure, deliberately
  — different plugins have wildly different data shapes (a clipboard
  event has different fields than an OCR event), and forcing one
  schema across all of them would be worse than a documented
  per-event_type payload convention. Each plugin module documents its
  own payload shape near its emission point.
- `confidence` is optional (None = not applicable) — some plugins
  (window tracking) are always certain what they observed; others
  (OCR, especially) may have OCR-engine confidence scores worth
  carrying through to the reasoning engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# Documented conventions — not an enforced enum, see docstring above.
EVENT_TYPE_CONVENTIONS = {
    "window_changed": "Active window/app changed (existing WindowInfo-based tracking)",
    "screen_text_detected": "OCR extracted text from the current screen",
    "clipboard_changed": "Clipboard content changed",
    "clipboard_secret_detected": "Clipboard content matched a secret/credential pattern",
    "browser_navigation": "Browser navigated to a new URL (from browser extension)",
    "editor_file_changed": "Active file changed in an editor (from VS Code extension)",
    "editor_diagnostic": "Compiler/linter error or warning surfaced (from VS Code extension)",
    "terminal_output": "New terminal output captured",
    "idle_started": "User became idle (no input) past a threshold",
    "idle_ended": "User resumed activity after being idle",
}


@dataclass(frozen=True, slots=True)
class ContextEvent:
    source: str
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def now(
        cls,
        source: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        confidence: float | None = None,
    ) -> "ContextEvent":
        return cls(
            source=source,
            event_type=event_type,
            payload=payload or {},
            confidence=confidence,
            captured_at=datetime.now(timezone.utc),
        )