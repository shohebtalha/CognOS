"""
PluginOrchestrator is the top-level loop that cognos capture runs,
driven by PluginRegistry.poll_all() instead of a single hardcoded
WindowInfoSource. Any number of plugins (window tracking, OCR,
clipboard, browser, VS Code later) feed into one ContextEvent stream,
processed uniformly here.

OCR handling (Day 15 decision, revised after live testing):
Originally, OcrObserver's periodic background poll (independent
~15s timer) populated a "most recent OCR text" that got attached to
context whenever a window-change event was flagged. Live testing
showed this was frequently stale or entirely wrong — the OCR poll and
the flag event are decoupled in time, so by the time a flag fired, the
screen content OCR last saw was often already different (confirmed:
a flagged Chrome error produced a suggestion referencing the WRONG
window's content, because OCR's last poll had captured the terminal,
not the browser).

FIX: on-demand OCR capture, triggered synchronously at the exact
moment a window-change event is flagged — not relying on the
background poll timing at all for this purpose. PluginOrchestrator
now optionally holds a Screenshotter + OcrEngine directly (same
interfaces as OcrObserver uses) and, only when a flag actually fires,
captures a fresh screenshot and runs OCR on it right then. This is
deliberately synchronous and only runs on the (rare, cooldown-gated)
flagged path — not on every tick — so it doesn't reintroduce the
"OCR running too often" cost concern that motivated OcrObserver's
slow poll interval in the first place.

OcrObserver's periodic background poll is NOT removed — it still
exists as a registered plugin and its events are still consumed (see
run_once below), kept for future use (e.g. a dedicated OCR-driven ML
feature, per the Day 15 note in ARCHITECTURE_STATE.md) even though its
output is no longer what feeds flag-time context.
"""

from __future__ import annotations

import base64
import logging
from typing import Protocol

from cogn_os.capture.types import WindowInfo
from cogn_os.config import Settings
from cogn_os.context.privacy_filter import is_sensitive
from cogn_os.ml.context_tracker import ContextTracker
from cogn_os.ml.feature_extractor import FeatureExtractor
from cogn_os.ml.suggestion_gate import SuggestionGate
from cogn_os.ocr.engine import OcrEngine
from cogn_os.plugins.registry import PluginRegistry
from cogn_os.plugins.translators import window_info_from_event
from cogn_os.screenshot.types import Screenshotter
from cogn_os.service.clock import Clock
from cogn_os.storage.repository import EventRepository, FeatureLogRepository

logger = logging.getLogger(__name__)


class OnFlagged(Protocol):
    def __call__(self, info: WindowInfo, history: list[WindowInfo], ocr_text: str | None) -> None: ...


class PluginOrchestrator:
    def __init__(
        self,
        registry: PluginRegistry,
        clock: Clock,
        settings: Settings,
        event_repo: EventRepository,
        suggestion_gate: SuggestionGate,
        on_flagged: OnFlagged,
        feature_log_repo: FeatureLogRepository | None = None,
        context_tracker: ContextTracker | None = None,
        feature_extractor: FeatureExtractor | None = None,
        tick_interval_seconds: float = 1.0,
        screenshotter: Screenshotter | None = None,
        ocr_engine: OcrEngine | None = None,
        on_demand_ocr_min_confidence: float = 50.0,
    ) -> None:
        self._registry = registry
        self._clock = clock
        self._settings = settings
        self._event_repo = event_repo
        self._suggestion_gate = suggestion_gate
        self._on_flagged = on_flagged
        self._feature_log_repo = feature_log_repo
        self._tracker = context_tracker or ContextTracker()
        self._extractor = feature_extractor or FeatureExtractor()
        self._tick_interval_seconds = tick_interval_seconds
        self._screenshotter = screenshotter
        self._ocr_engine = ocr_engine
        self._on_demand_ocr_min_confidence = on_demand_ocr_min_confidence

        self._running = False
        self.tick_count = 0
        self._last_ocr_text: str | None = None

    def run_once(self) -> list[str]:
        self.tick_count += 1
        events = self._registry.poll_all()
        processed_types: list[str] = []

        for event in events:
            if event.event_type == "screen_text_detected":
                processed_types.append(event.event_type)
                continue

            info = window_info_from_event(event)
            if info is None:
                logger.debug("no processing path yet for event_type=%r from source=%r",
                             event.event_type, event.source)
                continue

            self._process_window_event(info)
            processed_types.append(event.event_type)

        return processed_types

    def _capture_ocr_on_demand(self) -> str | None:
        if self._screenshotter is None or self._ocr_engine is None:
            return None
        try:
            screenshot = self._screenshotter.capture()
            if screenshot is None:
                return None
            image_bytes = base64.b64decode(screenshot.image_b64)
            result = self._ocr_engine.extract_text(image_bytes)
            if not result.text or result.mean_confidence < self._on_demand_ocr_min_confidence:
                return None
            return result.text
        except Exception:
            logger.exception("on-demand OCR capture failed")
            return None

    def _process_window_event(self, info: WindowInfo) -> None:
        if is_sensitive(info):
            logger.info("sensitive window blocked from storage/processing: %s", info.app_name)
            return

        self._event_repo.add(info)

        features = self._extractor.extract(
            current=info,
            previous=self._tracker.previous,
            history=self._tracker.history,
            last_llm_call_at=self._tracker.last_llm_call_at,
            apps_seen_today=self._tracker.apps_seen_today,
        )
        self._tracker.record_event(info)
        self._tracker.set_previous(info)

        try:
            model_says_flag = self._suggestion_gate.should_flag(features)
        except Exception:
            logger.exception("suggestion gate failed; treating as not-flagged")
            model_says_flag = False

        cooldown_elapsed = (
            self._tracker.last_llm_call_at is None
            or (info.captured_at - self._tracker.last_llm_call_at).total_seconds()
            >= self._settings.min_seconds_between_llm_calls
        )
        flagged = model_says_flag and cooldown_elapsed

        if self._feature_log_repo is not None:
            probability = getattr(
                self._suggestion_gate, "predict_probability", lambda f: float(model_says_flag)
            )(features)
            fdict = features.to_dict()
            fdict["app_category"] = fdict["app_category"].value
            self._feature_log_repo.add(info, fdict, probability=probability, flagged=flagged)

        if flagged:
            self._tracker.record_llm_call(info.captured_at)
            ocr_text = self._capture_ocr_on_demand()
            self._on_flagged(info, self._tracker.history, ocr_text)

    def run(self, max_ticks: int | None = None) -> None:
        self._running = True
        ticks = 0
        while self._running:
            self.run_once()
            ticks += 1
            if max_ticks is not None and ticks >= max_ticks:
                break
            self._clock.sleep(self._tick_interval_seconds)

    def stop(self) -> None:
        self._running = False