"""
Real OcrEngine backed by pytesseract (a wrapper around the Tesseract
OCR binary, which must be installed separately — this is a genuine
system dependency, not a pure-Python package, documented in the setup
instructions this ships alongside).

Confidence filtering: Tesseract reports per-word confidence; words
below MIN_WORD_CONFIDENCE are excluded from the returned text, since
low-confidence OCR output (garbled text from icons, decorative fonts,
etc.) is worse than no text at all for downstream LLM reasoning — a
wrong "read" is a direct path back to the hallucination problem
already solved in Day 12/13.
"""

from __future__ import annotations

import io
import logging

from cogn_os.ocr.engine import OcrEngine, OcrResult

logger = logging.getLogger(__name__)

MIN_WORD_CONFIDENCE = 40.0  # pytesseract confidence scale is 0-100


class TesseractOcrEngine(OcrEngine):
    def __init__(self, tesseract_cmd: str | None = None) -> None:
        try:
            import pytesseract
        except ImportError as e:
            raise RuntimeError("pytesseract not installed. pip install pytesseract") from e

        self._pytesseract = pytesseract
        if tesseract_cmd:
            self._pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def extract_text(self, image_bytes: bytes) -> OcrResult:
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes))
            data = self._pytesseract.image_to_data(
                img, output_type=self._pytesseract.Output.DICT
            )

            words: list[str] = []
            confidences: list[float] = []
            for text, conf in zip(data["text"], data["conf"]):
                text = text.strip()
                conf_value = float(conf)
                if text and conf_value >= MIN_WORD_CONFIDENCE:
                    words.append(text)
                    confidences.append(conf_value)

            if not words:
                return OcrResult(text="", mean_confidence=0.0)

            return OcrResult(
                text=" ".join(words),
                mean_confidence=sum(confidences) / len(confidences),
            )
        except Exception:
            logger.exception("OCR extraction failed")
            return OcrResult(text="", mean_confidence=0.0)