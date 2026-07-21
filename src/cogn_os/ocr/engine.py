"""
OcrEngine abstracts the OCR backend (Tesseract via pytesseract today,
potentially a Windows-native OCR API later if pytesseract proves too
slow/inaccurate in live testing — that evaluation happens after this
lands, not assumed in advance). Same interface-first pattern as every
other external dependency in this codebase: the plugin layer depends
on this abstraction, never on pytesseract directly, so tests never
need Tesseract installed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OcrResult:
    text: str
    mean_confidence: float  # 0-100, pytesseract's convention; 0 if no text detected


class OcrEngine(ABC):
    @abstractmethod
    def extract_text(self, image_bytes: bytes) -> OcrResult:
        """image_bytes: raw image bytes (e.g. JPEG/PNG), not base64.
        Must never raise — return OcrResult(text="", mean_confidence=0.0)
        on any failure, same 'never crash the caller' contract as every
        other Observer-adjacent component in this codebase."""
        raise NotImplementedError