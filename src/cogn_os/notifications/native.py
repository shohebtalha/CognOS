from __future__ import annotations

import logging
import platform
import base64
import subprocess

from cogn_os.storage.repository import AssistantCardDTO

logger = logging.getLogger(__name__)


class NativeNotifier:
    def __init__(self, enabled: bool = True, app_name: str = "CognOS") -> None:
        self._enabled = enabled
        self._app_name = app_name
        self._toaster = None
        self._windows = platform.system().lower() == "windows"
        if not enabled or platform.system().lower() != "windows":
            return
        try:
            from win10toast import ToastNotifier

            self._toaster = ToastNotifier()
        except Exception as exc:
            logger.warning("win10toast unavailable; using PowerShell notification fallback: %s", exc)

    @property
    def available(self) -> bool:
        return self._enabled and self._windows

    def notify_card(self, card: AssistantCardDTO) -> None:
        if not self.available:
            return
        message = f"{card.title}\n{card.summary}"
        if self._toaster is None:
            self._notify_with_powershell(message)
            return
        try:
            self._toaster.show_toast(
                self._app_name,
                message,
                duration=8,
                threaded=True,
            )
        except Exception:
            logger.exception("failed to show native notification")
            self._notify_with_powershell(message)

    def _notify_with_powershell(self, message: str) -> None:
        title = _ps_string(self._app_name)
        text = _ps_string(message)
        script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.BalloonTipTitle = {title}
$notify.BalloonTipText = {text}
$notify.Visible = $true
$notify.ShowBalloonTip(8000)
Start-Sleep -Seconds 9
$notify.Dispose()
"""
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            logger.exception("failed to show PowerShell notification")


def _ps_string(value: str) -> str:
    return "'" + value.replace("'", "''").replace("\r", " ").replace("\n", " ") + "'"
