from __future__ import annotations

from pathlib import Path

from cogn_os.plugins.events import ContextEvent
from cogn_os.plugins.observer import Observer


class TerminalTranscriptObserver(Observer):
    """Watches a PowerShell transcript file and emits new terminal output."""

    name = "terminal_transcript"

    def __init__(self, transcript_path: Path, poll_interval: float = 1.0) -> None:
        self._path = transcript_path
        self._poll_interval = poll_interval
        self._offset = 0

    @property
    def poll_interval_seconds(self) -> float:
        return self._poll_interval

    def poll(self) -> list[ContextEvent]:
        if not self._path.exists():
            return []
        try:
            size = self._path.stat().st_size
            if size < self._offset:
                self._offset = 0
            if size == self._offset:
                return []
            with self._path.open("r", encoding="utf-8", errors="ignore") as f:
                f.seek(self._offset)
                chunk = f.read(8000)
                self._offset = f.tell()
        except OSError:
            return []

        text = chunk.strip()
        if not text:
            return []
        return [ContextEvent.now(
            source=self.name,
            event_type="terminal_output",
            payload={"text": text, "path": str(self._path)},
            confidence=0.9,
        )]
