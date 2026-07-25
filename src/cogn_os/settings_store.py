from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class UserSettings:
    desktop_monitor_enabled: bool = True
    ocr_monitor_enabled: bool = True
    clipboard_monitor_enabled: bool = False
    native_notifications_enabled: bool = True
    native_notification_min_severity: str = "warning"
    llm_model: str = "llama3.2:latest"
    watched_paths: list[str] | None = None


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.home() / ".cognos" / "settings.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> UserSettings:
        if not self._path.exists():
            settings = UserSettings(watched_paths=[])
            self.save(settings)
            return settings
        data = json.loads(self._path.read_text(encoding="utf-8"))
        defaults = asdict(UserSettings(watched_paths=[]))
        defaults.update(data)
        return UserSettings(**defaults)

    def save(self, settings: UserSettings) -> UserSettings:
        self._path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
        return settings

    def update(self, patch: dict) -> UserSettings:
        current = asdict(self.load())
        allowed = set(current)
        current.update({k: v for k, v in patch.items() if k in allowed})
        return self.save(UserSettings(**current))
