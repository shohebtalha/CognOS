"""
Generates a tiny deterministic test JPEG so test_pil_screenshotter.py
can verify PilScreenshotter's downscale+encode logic without depending
on ImageGrab (which needs a real display). Run once; the output is
committed to the repo so tests don't regenerate it on every run.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def generate() -> Path:
    img = Image.new("RGB", (2000, 1500), color=(120, 160, 200))
    out_path = Path(__file__).parent / "sample_screen.jpg"
    img.save(out_path, format="JPEG", quality=90)
    return out_path


if __name__ == "__main__":
    path = generate()
    print(f"wrote {path}")