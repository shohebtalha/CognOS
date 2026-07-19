"""
Code-level privacy filtering — decides whether a window is sensitive
enough that NOTHING about it (title, screenshot, context) should ever
reach an LLM, local or cloud. This exists because prompt-level
instructions ("don't comment on banking screens") were shown in live
testing to be unreliable, especially with smaller local models —
enforcement belongs in code, not in hoping the model listens.

Pattern-matches against window titles for common sensitive-content
signals. Deliberately conservative (biased toward over-blocking) since
the cost of skipping a legitimate suggestion is far lower than the
cost of leaking sensitive content to any LLM call.
"""

from __future__ import annotations

import re

from cogn_os.capture.types import WindowInfo

SENSITIVE_TITLE_PATTERNS = [
    r"\bbank(ing)?\b",
    r"\bpassword\b",
    r"\blogin\b",
    r"\bsign.?in\b",
    r"\bpaypal\b",
    r"\bcredit card\b",
    r"\bssn\b",
    r"\bsocial security\b",
    r"\btax(es)?\b",
    r"\bwallet\b",
    r"\bcrypto\b",
    r"1password|lastpass|bitwarden|keepass",
]

SENSITIVE_APP_NAMES = {
    "1password.exe", "lastpass.exe", "keepass.exe", "bitwarden.exe",
}

_compiled_patterns = [re.compile(p, re.IGNORECASE) for p in SENSITIVE_TITLE_PATTERNS]


def is_sensitive(info: WindowInfo) -> bool:
    if info.app_name.lower() in SENSITIVE_APP_NAMES:
        return True
    return any(pattern.search(info.window_title) for pattern in _compiled_patterns)