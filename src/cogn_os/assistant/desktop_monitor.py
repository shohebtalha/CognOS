from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from cogn_os.assistant.runtime import AssistantRuntime
from cogn_os.capture.windows_source import WindowsWindowInfoSource
from cogn_os.config import Settings
from cogn_os.eventing.bus import EventBus
from cogn_os.notifications.native import NativeNotifier
from cogn_os.plugins.clipboard_observer import ClipboardObserver
from cogn_os.plugins.ocr_observer import OcrObserver
from cogn_os.plugins.registry import PluginRegistry
from cogn_os.plugins.window_observer import WindowObserver
from cogn_os.service.clock import RealClock
from cogn_os.storage.repository import EventRepository

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MonitorStatus:
    running: bool = False
    registered_plugins: list[str] = field(default_factory=list)
    last_error: str | None = None
    events_seen: int = 0
    cards_emitted: int = 0
    connectors: dict[str, str] = field(default_factory=dict)


class DesktopMonitor:
    """Always-on observer bridge used by the desktop product runtime."""

    def __init__(
        self,
        settings: Settings,
        runtime: AssistantRuntime,
        event_repo: EventRepository,
        bus: EventBus,
    ) -> None:
        self._settings = settings
        self._runtime = runtime
        self._event_repo = event_repo
        self._bus = bus
        self._clock = RealClock()
        self._registry = PluginRegistry(self._clock)
        self._notifier = NativeNotifier(enabled=settings.native_notifications_enabled)
        self._task: asyncio.Task | None = None
        self.status = MonitorStatus()
        self._register_default_observers()

    def start(self) -> None:
        if self._task is not None or not self._settings.desktop_monitor_enabled:
            return
        self.status.running = True
        self.status.registered_plugins = self._registry.registered_names
        self._task = asyncio.create_task(self._run(), name="cognos-desktop-monitor")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        self.status.running = False

    async def _run(self) -> None:
        while True:
            try:
                events = await asyncio.to_thread(self._registry.poll_all)
                self.status.events_seen += len(events)
                for event in events:
                    self._bus.publish("context_event", {
                        "source": event.source,
                        "event_type": event.event_type,
                        "payload": event.payload,
                        "confidence": event.confidence,
                        "captured_at": event.captured_at.isoformat(),
                    })
                    if event.event_type == "window_changed":
                        from cogn_os.plugins.translators import window_info_from_event

                        info = window_info_from_event(event)
                        if info is not None:
                            self._event_repo.add(info)
                cards = self._runtime.ingest(events)
                for card in cards:
                    if _should_notify(card.severity, self._settings.native_notification_min_severity):
                        self._notifier.notify_card(card)
                self.status.cards_emitted += len(cards)
                self.status.last_error = None
            except Exception as exc:
                logger.exception("desktop monitor tick failed")
                self.status.last_error = f"{type(exc).__name__}: {exc}"
            await asyncio.sleep(self._settings.monitor_tick_seconds)

    def _register_default_observers(self) -> None:
        try:
            self._registry.register(WindowObserver(
                WindowsWindowInfoSource(),
                poll_interval=self._settings.poll_interval_seconds,
            ))
        except Exception as exc:
            self.status.last_error = f"Window observer unavailable: {exc}"

        if self._settings.clipboard_monitor_enabled:
            self._registry.register(ClipboardObserver(enabled=True))
            self.status.connectors["clipboard"] = "enabled"
        else:
            self.status.connectors["clipboard"] = "disabled"

        if self._settings.ocr_monitor_enabled:
            try:
                from cogn_os.ocr.tesseract_engine import TesseractOcrEngine
                from cogn_os.screenshot.pil_screenshotter import PilScreenshotter

                self._registry.register(OcrObserver(
                    PilScreenshotter(),
                    TesseractOcrEngine(),
                    poll_interval=self._settings.ocr_poll_interval_seconds,
                ))
                self.status.connectors["ocr"] = "enabled"
            except Exception as exc:
                logger.warning("OCR observer unavailable: %s", exc)
                self.status.last_error = f"OCR observer unavailable: {exc}"
                self.status.connectors["ocr"] = "unavailable"

        self.status.connectors.setdefault("window_tracker", "enabled")
        self.status.connectors.setdefault("browser_extension", "available")
        self.status.connectors.setdefault("vscode_extension", "available")


_SEVERITY_RANK = {"info": 0, "success": 0, "warning": 1, "critical": 2}


def _should_notify(severity: str, minimum: str) -> bool:
    return _SEVERITY_RANK.get(severity, 0) >= _SEVERITY_RANK.get(minimum, 1)
