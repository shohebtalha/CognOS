"""
PluginOrchestrator is the new top-level loop, replacing CaptureLoop as
the thing cognos capture actually runs. Where CaptureLoop was hardwired
to one WindowInfoSource, this is driven by PluginRegistry.poll_all() —
any number of plugins (window tracking today; OCR, clipboard, browser,
VS Code later) feed into one ContextEvent stream, which this class
processes uniformly.

Behavior preservation, deliberate: for window_changed events specifically,
this reproduces exactly what build_ml_gated_loop (service/wiring.py)
already did — log to storage, extract features, run the ML gate, apply
the cooldown, filter sensitive content, call the reasoning provider.
Non-window events currently pass through PluginRegistry but are not
yet acted upon (no feature extraction path exists for them yet) —
that's the next real piece of work once OCR/clipboard plugins land,
not scope for this migration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Protocol

from cogn_os.capture.types import WindowInfo
from cogn_os.config import Settings
from cogn_os.context.privacy_filter import is_sensitive
from cogn_os.ml.context_tracker import ContextTracker
from cogn_os.ml.feature_extractor import FeatureExtractor
from cogn_os.ml.suggestion_gate import SuggestionGate
from cogn_os.plugins.registry import PluginRegistry
from cogn_os.plugins.translators import window_info_from_event
from cogn_os.service.clock import Clock
from cogn_os.storage.repository import EventRepository, FeatureLogRepository

logger = logging.getLogger(__name__)


class OnFlagged(Protocol):
    def __call__(self, info: WindowInfo, history: list[WindowInfo]) -> None: ...


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

        self._running = False
        self.tick_count = 0

    def run_once(self) -> list[str]:
        """Poll all registered plugins once, process any resulting
        events. Returns the list of event_types processed (mainly for
        test/debug visibility)."""
        self.tick_count += 1
        events = self._registry.poll_all()
        processed_types: list[str] = []

        for event in events:
            info = window_info_from_event(event)
            if info is None:
                # Non-window event (OCR, clipboard, etc.) — no
                # processing path yet. Logged at debug level so it's
                # visible during development without being noisy in
                # normal operation.
                logger.debug("no processing path yet for event_type=%r from source=%r",
                             event.event_type, event.source)
                continue

            self._process_window_event(info)
            processed_types.append(event.event_type)

        return processed_types

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
            self._on_flagged(info, self._tracker.history)

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