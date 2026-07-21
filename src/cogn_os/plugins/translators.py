"""
Translates ContextEvents back into the domain types the existing ML
gate / feature extractor / privacy filter / reasoning pipeline expect.

This exists so today's migration doesn't require rewriting
FeatureExtractor, ModelSuggestionGate, or is_sensitive() — all of
which are built around WindowInfo, tested, and working. Once
non-window plugins (OCR, clipboard) need to influence the ML gate
directly, SuggestionFeatures itself will need new fields (same pattern
as Day 10's title_semantic_similarity_to_previous) — that's future
work, not this migration's job. This translator's only job today is
"make ContextEvent-based orchestration produce identical inputs to
what CaptureLoop already produced," so the migration is behavior-
preserving, not behavior-changing.
"""

from __future__ import annotations

from cogn_os.capture.types import WindowInfo
from cogn_os.plugins.events import ContextEvent


def window_info_from_event(event: ContextEvent) -> WindowInfo | None:
    """Returns None if this event isn't a window_changed event — callers
    should skip non-window events for now (OCR/clipboard events don't
    yet have a WindowInfo-shaped translation, by design; see docstring)."""
    if event.event_type != "window_changed":
        return None
    return WindowInfo(
        app_name=event.payload["app_name"],
        window_title=event.payload["window_title"],
        captured_at=event.captured_at,
    )