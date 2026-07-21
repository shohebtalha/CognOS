"""
Generates a deterministic test image with known text burned in, so
test_tesseract_engine.py can verify real OCR extraction against a
ground truth without depending on a live screen capture.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def generate() -> Path:
    img = Image.new("RGB", (600, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 50), "ModuleNotFoundError: No module named requests", fill=(0, 0, 0))
    out_path = Path(__file__).parent / "ocr_sample.png"
    img.save(out_path, format="PNG")
    return out_path


if __name__ == "__main__":
    path = generate()
    print(f"wrote {path}")