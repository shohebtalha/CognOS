"""
App exclusion filtering, extracted as its own function rather than
buried inline in the loop — makes it independently testable and gives
Day 8 (privacy filters) a clear, single place to extend without
touching loop control flow.
"""

from __future__ import annotations

from cogn_os.capture.types import WindowInfo


def is_excluded(info: WindowInfo, excluded_apps: frozenset[str]) -> bool:
    """Case-insensitive match against the excluded app set."""
    return info.app_name.lower() in {a.lower() for a in excluded_apps}