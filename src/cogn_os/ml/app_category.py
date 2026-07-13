"""
Maps a process name to a coarse category. This is a hand-authored
lookup table, not a model — deliberately simple and fast, since it's a
*feature* feeding into the real model (Day 6), not the thing being
learned itself. Unknown apps fall back to "other" rather than raising,
since the categorizer must never crash the capture pipeline.

Extending this table over time (as new apps are observed) is a cheap,
low-risk way to improve model input quality without retraining logic.
"""

from __future__ import annotations

from enum import Enum


class AppCategory(str, Enum):
    IDE = "ide"
    BROWSER = "browser"
    TERMINAL = "terminal"
    CHAT = "chat"
    DOCUMENT = "document"
    OTHER = "other"


_CATEGORY_MAP: dict[str, AppCategory] = {
    # IDEs / editors
    "code.exe": AppCategory.IDE,
    "devenv.exe": AppCategory.IDE,
    "pycharm64.exe": AppCategory.IDE,
    "idea64.exe": AppCategory.IDE,
    "sublime_text.exe": AppCategory.IDE,
    "notepad++.exe": AppCategory.IDE,
    # Browsers
    "chrome.exe": AppCategory.BROWSER,
    "firefox.exe": AppCategory.BROWSER,
    "msedge.exe": AppCategory.BROWSER,
    "brave.exe": AppCategory.BROWSER,
    # Terminals
    "windowsterminal.exe": AppCategory.TERMINAL,
    "cmd.exe": AppCategory.TERMINAL,
    "powershell.exe": AppCategory.TERMINAL,
    "pwsh.exe": AppCategory.TERMINAL,
    # Chat / comms
    "slack.exe": AppCategory.CHAT,
    "discord.exe": AppCategory.CHAT,
    "whatsapp.root.exe": AppCategory.CHAT,
    "teams.exe": AppCategory.CHAT,
    "outlook.exe": AppCategory.CHAT,
    # Documents
    "winword.exe": AppCategory.DOCUMENT,
    "excel.exe": AppCategory.DOCUMENT,
    "acrobat.exe": AppCategory.DOCUMENT,
    "notepad.exe": AppCategory.DOCUMENT,
}


def categorize(app_name: str) -> AppCategory:
    return _CATEGORY_MAP.get(app_name.strip().lower(), AppCategory.OTHER)