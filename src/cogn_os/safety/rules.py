from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuleFinding:
    severity: str
    title: str
    detail: str


class RuleEngine:
    _PHISHING = re.compile(r"(login|verify|account|wallet).*(free|urgent|suspend)|\.zip/|xn--", re.I)
    _PIRACY = re.compile(r"(crack|keygen|torrent|nulled|serial key)", re.I)
    _DOWNLOAD = re.compile(r"\.(exe|msi|bat|cmd|ps1|scr)$", re.I)

    def evaluate_text(self, text: str) -> list[RuleFinding]:
        findings: list[RuleFinding] = []
        if self._PHISHING.search(text):
            findings.append(RuleFinding("high", "Suspicious page or message", "The visible text resembles phishing or account-pressure language."))
        if self._PIRACY.search(text):
            findings.append(RuleFinding("medium", "Unsafe download context", "The visible text references cracks, keygens, torrents, or serial keys."))
        if self._DOWNLOAD.search(text.strip()):
            findings.append(RuleFinding("medium", "Executable download", "CognOS noticed a potentially executable file name."))
        return findings
