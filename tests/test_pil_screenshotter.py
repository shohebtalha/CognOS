"""
These tests monkeypatch PIL.ImageGrab.grab to return our fixture image
instead of the real screen — this still exercises the *real* downscale
and JPEG-encode code path (no mocking of PilScreenshotter's internals),
just swaps out the one line that would otherwise need a real display.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

from cogn_os.screenshot.pil_screenshotter import PilScreenshotter

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_screen.jpg"


def _fake_grab():
    return Image.open(FIXTURE_PATH).copy()


def test_capture_downscales_to_max_dimension(monkeypatch):
    monkeypatch.setattr("PIL.ImageGrab.grab", _fake_grab)
    screenshotter = PilScreenshotter(max_dimension=500, jpeg_quality=70)

    shot = screenshotter.capture()

    assert shot is not None
    assert max(shot.width, shot.height) <= 500


def test_capture_produces_valid_base64_jpeg(monkeypatch):
    monkeypatch.setattr("PIL.ImageGrab.grab", _fake_grab)
    screenshotter = PilScreenshotter()

    shot = screenshotter.capture()

    assert shot is not None
    raw_bytes = base64.b64decode(shot.image_b64)
    img = Image.open(io.BytesIO(raw_bytes))
    assert img.format == "JPEG"


def test_capture_respects_custom_quality_setting(monkeypatch):
    monkeypatch.setattr("PIL.ImageGrab.grab", _fake_grab)
    low_quality = PilScreenshotter(jpeg_quality=10).capture()
    high_quality = PilScreenshotter(jpeg_quality=95).capture()

    assert low_quality is not None and high_quality is not None
    # Lower JPEG quality should produce a smaller payload for the same image.
    assert len(low_quality.image_b64) < len(high_quality.image_b64)


def test_capture_returns_none_on_failure(monkeypatch):
    def _raise():
        raise RuntimeError("no display available")

    monkeypatch.setattr("PIL.ImageGrab.grab", _raise)
    screenshotter = PilScreenshotter()

    assert screenshotter.capture() is None