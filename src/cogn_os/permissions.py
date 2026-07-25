from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import platform


class PermissionState(str, Enum):
    GRANTED = "granted"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"
    NEEDS_USER_ACTION = "needs_user_action"


@dataclass(frozen=True, slots=True)
class PermissionStatus:
    key: str
    label: str
    state: PermissionState
    detail: str


def permission_inventory() -> list[PermissionStatus]:
    system = platform.system().lower()
    windows = system == "windows"
    return [
        PermissionStatus("active_window", "Active window", PermissionState.GRANTED if windows else PermissionState.UNAVAILABLE, "Tracks app and window title changes."),
        PermissionStatus("screenshots", "Screenshots and OCR", PermissionState.NEEDS_USER_ACTION, "Requires screen capture access and a local Tesseract install."),
        PermissionStatus("clipboard", "Clipboard", PermissionState.NEEDS_USER_ACTION, "Disabled until the user enables clipboard monitoring."),
        PermissionStatus("filesystem", "File changes", PermissionState.NEEDS_USER_ACTION, "Watches only folders explicitly configured by the user."),
        PermissionStatus("browser", "Browser URLs", PermissionState.NEEDS_USER_ACTION, "Uses browser integration when a user-installed connector is available."),
        PermissionStatus("microphone", "Meeting audio", PermissionState.NEEDS_USER_ACTION, "Requires microphone permission and local transcription model."),
        PermissionStatus("notifications", "Notifications", PermissionState.UNAVAILABLE if windows else PermissionState.UNAVAILABLE, "Native notification reading is OS-restricted; CognOS falls back to visible-screen OCR."),
    ]
