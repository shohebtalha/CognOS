"""
Cosine similarity, extracted as its own tiny testable function rather
than inlined wherever it's needed — this is the exact metric Day 10's
semantic change detection thresholds against, so it deserves its own
unit tests independent of any embedding model.
"""

from __future__ import annotations

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))