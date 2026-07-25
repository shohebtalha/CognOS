from __future__ import annotations

from datetime import datetime, timezone

from cogn_os.plugins.events import ContextEvent
from cogn_os.plugins.observer import Observer


class ClipboardObserver(Observer):
    name = "clipboard"

    def __init__(self, enabled: bool = False) -> None:
        self._enabled = enabled
        self._last_text: str | None = None

    def poll(self) -> list[ContextEvent]:
        if not self._enabled:
            return []
        try:
            import pyperclip
            text = pyperclip.paste()
        except Exception:
            return []
        if not text or text == self._last_text:
            return []
        self._last_text = text
        redacted = text[:500]
        return [ContextEvent(
            source=self.name,
            event_type="clipboard_changed",
            payload={"text": redacted, "length": len(text)},
            confidence=1.0,
            captured_at=datetime.now(timezone.utc),
        )]
