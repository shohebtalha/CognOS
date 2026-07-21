"""
Test double for OcrEngine — returns a scripted result regardless of
input image bytes, no real Tesseract dependency.
"""

from __future__ import annotations

from cogn_os.ocr.engine import OcrEngine, OcrResult


class FakeOcrEngine(OcrEngine):
    def __init__(self, text: str = "", mean_confidence: float = 90.0) -> None:
        self._text = text
        self._mean_confidence = mean_confidence
        self.call_count = 0
        self.received_image_bytes: list[bytes] = []

    def extract_text(self, image_bytes: bytes) -> OcrResult:
        self.call_count += 1
        self.received_image_bytes.append(image_bytes)
        return OcrResult(text=self._text, mean_confidence=self._mean_confidence)

    def set_next(self, text: str, mean_confidence: float = 90.0) -> None:
        self._text = text
        self._mean_confidence = mean_confidence