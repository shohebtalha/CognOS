"""
Windows implementation of WindowInfoSource, using pygetwindow + psutil +
ctypes (for the PID lookup via GetWindowThreadProcessId).

Imports of Windows-only packages happen inside __init__, not at module
level, so this module can still be *imported* (e.g. for type-checking or
by a factory function) on non-Windows systems without raising ImportError
at import time — only if you actually try to instantiate it there.
"""

from __future__ import annotations

from cogn_os.capture.types import WindowInfo, WindowInfoSource


class WindowsWindowInfoSource(WindowInfoSource):
    def __init__(self) -> None:
        try:
            import ctypes  # noqa: F401
            import pygetwindow  # noqa: F401
            import psutil  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "WindowsWindowInfoSource requires the 'windows' extra: "
                "pip install '.[windows]'"
            ) from e

    def get_active_window(self) -> WindowInfo | None:
        import ctypes

        import psutil
        import pygetwindow as gw

        try:
            win = gw.getActiveWindow()
            if win is None:
                return None
            title = win.title or ""

            hwnd = win._hWnd  # noqa: SLF001 - pygetwindow exposes no public accessor
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))  # type: ignore[attr-defined]

            try:
                proc_name = psutil.Process(pid.value).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                proc_name = "unknown"

            return WindowInfo.now(app_name=proc_name, window_title=title)
        except Exception:
            # A single failed poll should never crash the capture loop.
            # The loop itself logs and retries on the next tick.
            return None