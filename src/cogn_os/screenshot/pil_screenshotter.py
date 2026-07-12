"""
Real Screenshotter implementation using Pillow's ImageGrab (Windows/macOS
only — Linux would need a different backend, out of scope here since
this is a Windows-first project per PLAN.md).

Downscaling before encoding matters for two reasons: it keeps the
base64 payload small enough to stay well under the LLM API's per-request
size limits, and it directly reduces token/cost per call (Day 12+).
"""

from __future__ import annotations

import base64
import io
import logging

from cogn_os.screenshot.types import Screenshot, Screenshotter

logger = logging.getLogger(__name__)

DEFAULT_MAX_DIMENSION = 1280
DEFAULT_JPEG_QUALITY = 70


class PilScreenshotter(Screenshotter):
    def __init__(
        self,
        max_dimension: int = DEFAULT_MAX_DIMENSION,
        jpeg_quality: int = DEFAULT_JPEG_QUALITY,
    ) -> None:
        self._max_dimension = max_dimension
        self._jpeg_quality = jpeg_quality

    def capture(self) -> Screenshot | None:
        try:
            from PIL import ImageGrab
        except ImportError:
            logger.error("Pillow not installed; install the 'windows' extra")
            return None

        try:
            img = ImageGrab.grab()
            img.thumbnail((self._max_dimension, self._max_dimension))

            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=self._jpeg_quality)
            image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

            return Screenshot.now(
                image_b64=image_b64,
                width=img.width,
                height=img.height,
                format="jpeg",
            )
        except Exception:
            logger.exception("screenshot capture failed")
            return None