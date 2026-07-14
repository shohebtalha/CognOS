"""
Evaluation, deliberately not just accuracy — this dataset is imbalanced
(~10-20% positive rate by design, see docs/ML_DATASET.md), so accuracy
alone would be misleading (a model that always predicts "not worth
flagging" would score ~85% accuracy while being useless). Precision,
recall, and F1 on the positive class are the metrics that actually
matter for this problem: precision protects against annoying the user
with bad suggestions, recall protects against missing genuinely useful
moments.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline


@dataclass(frozen=True)
class EvaluationResult:
    model_name: str
    precision: float
    recall: float
    f1: float
    true_negatives: int
    false_positives: int
    false_negatives: int
    true_positives: int

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_model(
    pipeline: Pipeline, x_test: pd.DataFrame, y_test: pd.Series, model_name: str
) -> EvaluationResult:
    y_pred = pipeline.predict(x_test)

    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()

    return EvaluationResult(
        model_name=model_name,
        precision=round(float(precision), 4),
        recall=round(float(recall), 4),
        f1=round(float(f1), 4),
        true_negatives=int(tn),
        false_positives=int(fp),
        false_negatives=int(fn),
        true_positives=int(tp),
    )