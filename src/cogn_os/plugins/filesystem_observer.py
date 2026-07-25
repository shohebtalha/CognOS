from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from cogn_os.plugins.events import ContextEvent
from cogn_os.plugins.observer import Observer


class FileSystemObserver(Observer):
    name = "filesystem"

    def __init__(self, roots: list[Path] | None = None) -> None:
        self._roots = roots or []
        self._seen: dict[str, float] = {}

    def poll(self) -> list[ContextEvent]:
        events: list[ContextEvent] = []
        for root in self._roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                try:
                    mtime = path.stat().st_mtime
                except OSError:
                    continue
                key = str(path)
                if key not in self._seen:
                    self._seen[key] = mtime
                    continue
                if self._seen[key] != mtime:
                    self._seen[key] = mtime
                    events.append(ContextEvent(
                        source=self.name,
                        event_type="file_changed",
                        payload={"path": key, "suffix": path.suffix},
                        confidence=1.0,
                        captured_at=datetime.now(timezone.utc),
                    ))
        return events
