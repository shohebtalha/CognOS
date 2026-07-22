"""
OcrObserver is the plugin that turns raw screen pixels into real text
ContextEvents — the single biggest upgrade from "sees window titles"
to "sees what's actually on screen."

Design decisions, stated explicitly:

- Polls much less often than window tracking (default 15s, vs. window
  tracking's 3s) — OCR is comparatively expensive (real CPU work per
  call) and screen text usually doesn't change meaningfully every few
  seconds the way window focus does.
- De-duplicates: only emits an event if the extracted text has
  MEANINGFULLY changed since the last poll (exact match check first,
  cheap; a more precise "did anything actually change" would need a
  diff/similarity threshold, deliberately deferred — exact-match
  de-dup is the simplest correct starting point, refine only if live
  testing shows too many near-duplicate events).
- Emits only text ABOVE a length threshold — very short OCR results
  (a handful of characters, common on mostly-blank screens or icon-only
  areas) are usually noise, not meaningful screen content.
- Uses the EXISTING Screenshotter interface (Day 4) rather than a new
  screen-capture path — this is the first real payoff of that
  interface having been built and sitting unused: no new screen-access
  code needed here at all.
"""

from __future__ import annotations

import base64
import logging

from cogn_os.ocr.engine import OcrEngine
from cogn_os.plugins.events import ContextEvent
from cogn_os.plugins.observer import Observer
from cogn_os.screenshot.types import Screenshotter

logger = logging.getLogger(__name__)

MIN_TEXT_LENGTH = 15  # characters; shorter results are treated as noise
DEFAULT_POLL_INTERVAL = 15.0


class OcrObserver(Observer):
    def __init__(
        self,
        screenshotter: Screenshotter,
        ocr_engine: OcrEngine,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        min_confidence: float = 50.0,
    ) -> None:
        self._screenshotter = screenshotter
        self._ocr_engine = ocr_engine
        self._poll_interval = poll_interval
        self._min_confidence = min_confidence
        self._last_text: str | None = None

    @property
    def name(self) -> str:
        return "ocr"

    @property
    def poll_interval_seconds(self) -> float:
        return self._poll_interval

    def poll(self) -> list[ContextEvent]:
        try:
            screenshot = self._screenshotter.capture()
            if screenshot is None:
                return []

            image_bytes = base64.b64decode(screenshot.image_b64)
            result = self._ocr_engine.extract_text(image_bytes)

            if len(result.text) < MIN_TEXT_LENGTH:
                return []
            if result.mean_confidence < self._min_confidence:
                return []
            if result.text == self._last_text:
                return []  # no meaningful change since last poll

            self._last_text = result.text
            return [
                ContextEvent.now(
                    source=self.name,
                    event_type="screen_text_detected",
                    payload={"text": result.text},
                    confidence=result.mean_confidence,
                )
            ]
        except Exception:
            logger.exception("OcrObserver.poll() failed")
            return []