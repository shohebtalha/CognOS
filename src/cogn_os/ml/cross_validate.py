"""
5-fold stratified cross-validation, reported alongside the single
train/test-split metrics from evaluate.py. A single split's F1 can vary
meaningfully run-to-run on a moderately sized dataset; reporting a
cross-validated mean +/- std is the more honest number to put in
metrics.json and to quote if asked "how good is your model" in an
interview.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline


@dataclass(frozen=True)
class CrossValResult:
    model_name: str
    metric: str
    fold_scores: list[float]
    mean: float
    std: float

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "metric": self.metric,
            "fold_scores": self.fold_scores,
            "mean": self.mean,
            "std": self.std,
        }


def cross_validate_model(
    pipeline: Pipeline, x: pd.DataFrame, y: pd.Series, model_name: str,
    n_splits: int = 5, scoring: str = "f1", seed: int = 42,
) -> CrossValResult:
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    scores = cross_val_score(pipeline, x, y, cv=cv, scoring=scoring)

    return CrossValResult(
        model_name=model_name,
        metric=scoring,
        fold_scores=[round(float(s), 4) for s in scores],
        mean=round(float(np.mean(scores)), 4),
        std=round(float(np.std(scores)), 4),
    )