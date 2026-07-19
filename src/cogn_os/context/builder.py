"""
Builds the actual context_summary sent to the LLM, from real recent
history — replacing the Day 12 placeholder (f"Recently active: {app}"),
which gave the model almost nothing to reason from and was the direct
cause of the fabrication problems observed in live testing.

Deliberately a plain function, not a class needing DI — it has no
external dependencies (no DB, no network), just transforms data
already available from ContextTracker/EventRepository into text.
"""

from __future__ import annotations

from cogn_os.capture.types import WindowInfo

MAX_HISTORY_LINES = 8


def build_context_summary(history: list[WindowInfo], current: WindowInfo) -> str:
    """history: recent events, chronological (oldest first), NOT
    including `current`. Produces a short, factual, bulleted recent-
    activity summary — deliberately plain and literal (no
    interpretation added) so the LLM's own reasoning isn't primed by
    summary-writer bias, and so nothing here could itself become a
    source of fabricated detail."""
    if not history:
        return "No prior activity recorded this session."

    recent = history[-MAX_HISTORY_LINES:]
    lines = [f"- {e.app_name}: {e.window_title}" for e in recent if e.window_title]
    if not lines:
        return "No prior activity with identifiable window titles."

    return "Recent activity (oldest to newest):\n" + "\n".join(lines)