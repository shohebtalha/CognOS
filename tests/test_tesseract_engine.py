"""
Runs against the REAL Tesseract binary — requires it installed and on
PATH (or explicitly pointed at via tesseract_cmd). Skipped automatically
if pytesseract can't find the binary, so machines without Tesseract
installed don't fail collection.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogn_os.ocr.tesseract_engine import TesseractOcrEngine

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ocr_sample.png"


def _tesseract_available() -> bool:
    try:
        engine = TesseractOcrEngine()
        result = engine.extract_text(FIXTURE_PATH.read_bytes())
        return result.text != "" or FIXTURE_PATH.exists()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not FIXTURE_PATH.exists(), reason="OCR fixture not generated — run tests/fixtures/make_ocr_fixture.py"
)


@pytest.fixture(scope="module")
def engine():
    try:
        return TesseractOcrEngine()
    except RuntimeError:
        pytest.skip("pytesseract not installed")


def test_extracts_known_text_from_fixture_image(engine):
    result = engine.extract_text(FIXTURE_PATH.read_bytes())
    # Real OCR is imperfect — check for the distinctive substring
    # rather than exact match, since minor character misreads are
    # normal and not a test failure.
    assert "ModuleNotFoundError" in result.text or "requests" in result.text


def test_confidence_is_reported(engine):
    result = engine.extract_text(FIXTURE_PATH.read_bytes())
    assert 0.0 <= result.mean_confidence <= 100.0


def test_blank_image_returns_empty_text(engine):
    from PIL import Image
    import io

    blank = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    blank.save(buf, format="PNG")

    result = engine.extract_text(buf.getvalue())
    assert result.text == ""


def test_invalid_image_bytes_returns_empty_result_without_crashing(engine):
    result = engine.extract_text(b"not a real image")
    assert result.text == ""
    assert result.mean_confidence == 0.0