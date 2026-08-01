from __future__ import annotations

import re

from cogn_os.assistant.types import AssistantAction, AssistantCard, CardSeverity, WorkspaceState
from cogn_os.ocr.error_detector import contains_error_signal
from cogn_os.plugins.events import ContextEvent
from cogn_os.safety.rules import RuleEngine


class OpportunityDetector:
    """Converts raw events into product-level assistant opportunities."""

    _SECRET = re.compile(r"(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}", re.I)
    _TERMINAL_FAILURE = re.compile(
        r"(command failed|exit_code=[1-9]|fatal:|error:|npm ERR!|docker: error|kubectl .*error|"
        r"permission denied|access is denied|cannot find|not recognized as)",
        re.I,
    )
    _UNSAFE_COMMAND = re.compile(r"\b(rm\s+-rf\s+/|format\s+[a-z]:|del\s+/s\s+/q\s+[a-z]:\\|git\s+reset\s+--hard)\b", re.I)

    def __init__(self, rule_engine: RuleEngine | None = None) -> None:
        self._rules = rule_engine or RuleEngine()

    def evaluate(self, event: ContextEvent, state: WorkspaceState) -> list[AssistantCard]:
        text = _event_text(event)
        cards: list[AssistantCard] = []

        if text and contains_error_signal(text):
            cards.append(AssistantCard(
                kind="debugging",
                severity=CardSeverity.CRITICAL,
                title="Error detected",
                summary="CognOS noticed an exception, compiler error, or failure message in the current workspace.",
                source=event.source,
                confidence=event.confidence or 0.95,
                actions=(
                    AssistantAction("explain_error", "Explain", "ask", {"prompt": text[:3000]}),
                    AssistantAction("suggest_fix", "Suggest fix", "ask", {"prompt": f"Suggest a fix for:\n{text[:3000]}"}),
                ),
                context={"event_type": event.event_type, "text": text[:3000]},
            ))

        if text and self._SECRET.search(text):
            cards.append(AssistantCard(
                kind="security",
                severity=CardSeverity.CRITICAL,
                title="Possible secret exposure",
                summary="A token, password, or API key-like value appears in visible text or clipboard content.",
                source=event.source,
                confidence=0.9,
                actions=(AssistantAction("rotate_secret", "Rotation steps", "ask", {"prompt": "Explain how to rotate a leaked secret safely."}),),
                context={"event_type": event.event_type},
            ))

        for finding in self._rules.evaluate_text(text):
            cards.append(AssistantCard(
                kind="safety",
                severity=CardSeverity.CRITICAL if finding.severity == "high" else CardSeverity.WARNING,
                title=finding.title,
                summary=finding.detail,
                source=event.source,
                confidence=0.85,
                actions=(AssistantAction("inspect_risk", "Inspect", "ask", {"prompt": text[:3000]}),),
                context={"event_type": event.event_type},
            ))

        if event.event_type == "file_changed" and str(event.payload.get("suffix", "")).lower() in {".py", ".ts", ".tsx", ".js", ".rs", ".go"}:
            cards.append(AssistantCard(
                kind="code",
                severity=CardSeverity.INFO,
                title="Code changed",
                summary=f"CognOS can index and reason over {event.payload.get('path')} if you want deeper help.",
                source=event.source,
                confidence=0.7,
                actions=(AssistantAction("index_file", "Index file", "index_file", {"path": event.payload.get("path")}),),
                context={"path": event.payload.get("path")},
            ))

        if event.event_type == "editor_diagnostic":
            diagnostics = event.payload.get("diagnostics", [])
            if isinstance(diagnostics, list) and diagnostics:
                first = diagnostics[0]
                message = str(first.get("message", "Editor diagnostic")) if isinstance(first, dict) else "Editor diagnostic"
                cards.append(AssistantCard(
                    kind="code",
                    severity=CardSeverity.WARNING,
                    title="Editor diagnostic detected",
                    summary=message,
                    source=event.source,
                    confidence=event.confidence or 0.95,
                    actions=(
                        AssistantAction("explain_diagnostic", "Explain", "ask", {"prompt": f"Explain and fix this diagnostic:\n{event.payload}"}),
                        AssistantAction("debug_steps", "Debug steps", "ask", {"prompt": f"Give concise debugging steps for:\n{event.payload}"}),
                    ),
                    context={"event_type": event.event_type, "diagnostics": diagnostics[:5]},
                ))

        if event.event_type == "browser_navigation":
            url = str(event.payload.get("url", ""))
            if url and self._looks_suspicious_url(url):
                cards.append(AssistantCard(
                    kind="safety",
                    severity=CardSeverity.WARNING,
                    title="Suspicious website",
                    summary="This URL has patterns often seen in phishing or deceptive sites.",
                    source=event.source,
                    confidence=0.82,
                    actions=(AssistantAction("inspect_site", "Inspect risk", "ask", {"prompt": f"Assess this URL for risk: {url}"}),),
                    context={"url": url, "title": event.payload.get("title", "")},
                ))

        if event.event_type == "download_started":
            filename = str(event.payload.get("filename", ""))
            danger = str(event.payload.get("danger", "unknown"))
            if danger not in {"safe", "accepted"} or filename.lower().endswith((".exe", ".msi", ".bat", ".cmd", ".ps1", ".scr")):
                cards.append(AssistantCard(
                    kind="safety",
                    severity=CardSeverity.WARNING,
                    title="Download needs attention",
                    summary=f"CognOS noticed a potentially risky download: {filename or event.payload.get('url', 'unknown file')}",
                    source=event.source,
                    confidence=0.9,
                    actions=(AssistantAction("download_safety", "Check safety", "ask", {"prompt": f"Assess this download metadata:\n{event.payload}"}),),
                    context={"download": event.payload},
                ))

        if event.event_type == "terminal_output":
            if self._UNSAFE_COMMAND.search(text):
                cards.append(AssistantCard(
                    kind="safety",
                    severity=CardSeverity.CRITICAL,
                    title="Dangerous command detected",
                    summary="Terminal output contains a command pattern that can delete or overwrite important work.",
                    source=event.source,
                    confidence=0.92,
                    actions=(AssistantAction("safe_terminal_steps", "Safer option", "ask", {"prompt": f"Suggest a safer alternative for this terminal activity:\n{text[:3000]}"}),),
                    context={"event_type": event.event_type, "text": text[:3000]},
                ))
            elif self._TERMINAL_FAILURE.search(text):
                cards.append(AssistantCard(
                    kind="terminal",
                    severity=CardSeverity.WARNING,
                    title="Terminal failure detected",
                    summary="A command appears to have failed. CognOS can explain the error and suggest the next step.",
                    source=event.source,
                    confidence=0.88,
                    actions=(
                        AssistantAction("explain_terminal", "Explain", "ask", {"prompt": f"Explain this terminal failure:\n{text[:3000]}"}),
                        AssistantAction("fix_terminal", "Fix", "ask", {"prompt": f"Give the likely fix for this terminal output:\n{text[:3000]}"}),
                    ),
                    context={"event_type": event.event_type, "text": text[:3000]},
                ))

        return cards

    def _looks_suspicious_url(self, url: str) -> bool:
        lower = url.lower()
        return any(marker in lower for marker in [
            "xn--", "login-", "verify-", "account-", "free-", "airdrop",
            "wallet", "keygen", "crack", "torrent"
        ])


def _event_text(event: ContextEvent) -> str:
    payload = event.payload
    if "text" in payload:
        return str(payload["text"])
    if "url" in payload:
        return str(payload["url"])
    if "path" in payload:
        return str(payload["path"])
    if "window_title" in payload:
        return str(payload["window_title"])
    return " ".join(str(v) for v in payload.values())
