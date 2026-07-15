"""
Retraining pipeline logic. Key design decisions, stated explicitly:

1. Cold-start blending: real labeled examples are usually scarce early
   on. Rather than fail outright below some arbitrary minimum, this
   blends real examples (if any) with the synthetic dataset, weighting
   real examples more heavily via sample duplication — a simple,
   explainable approach preferable to something like SMOTE for a small,
   mixed-provenance dataset like this.

2. Promotion gate: a newly retrained model REPLACES the production
   model only if its test-set F1 is >= the current production model's
   recorded F1 (from models/metrics.json). This prevents a retrain on a
   small, noisy batch of real feedback from silently regressing
   production quality — a real MLOps concern, not a toy one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from cogn_os.ml.cross_validate import cross_validate_model
from cogn_os.ml.dataset import cap_infinite_feature, load_dataset
from cogn_os.ml.evaluate import EvaluationResult, evaluate_model
from cogn_os.ml.features import SuggestionFeatures
from cogn_os.ml.train import build_pipeline, prepare_data, train_model

REAL_EXAMPLE_DUPLICATION_WEIGHT = 5  # each real labeled row counted 5x
CANDIDATE_MODELS = ["logistic_regression", "random_forest"]


@dataclass(frozen=True)
class RetrainResult:
    winner: str
    new_f1: float
    previous_f1: float | None
    promoted: bool
    real_examples_used: int
    synthetic_examples_used: int


def real_logs_to_dataframe(labeled_examples: list) -> pd.DataFrame:
    """Converts FeatureLogDTO objects (from FeatureLogRepository.labeled_examples())
    into the same flat schema as the synthetic CSV, so both can be concatenated."""
    rows = []
    for ex in labeled_examples:
        row = dict(ex.features)
        row["worth_flagging"] = ex.user_label
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=list(SuggestionFeatures.FEATURE_NAMES) + ["worth_flagging"])
    df = pd.DataFrame(rows)
    df["app_category"] = df["app_category"].astype("category")
    return df


def build_blended_dataset(synthetic_csv_path: Path, real_examples: list) -> pd.DataFrame:
    synthetic_df = load_dataset(synthetic_csv_path)
    real_df = real_logs_to_dataframe(real_examples)

    if len(real_df) > 0:
        real_df_weighted = pd.concat([real_df] * REAL_EXAMPLE_DUPLICATION_WEIGHT, ignore_index=True)
        blended = pd.concat([synthetic_df, real_df_weighted], ignore_index=True)
    else:
        blended = synthetic_df

    return blended


def load_previous_best_f1(metrics_path: Path) -> float | None:
    if not metrics_path.exists():
        return None
    metrics = json.loads(metrics_path.read_text())
    winner = metrics.get("winner")
    if winner is None:
        return None
    return metrics["results"][winner]["test_set"]["f1"]


def retrain(
    synthetic_csv_path: Path,
    real_examples: list,
    previous_metrics_path: Path,
) -> tuple[RetrainResult, dict, object]:
    """Returns (RetrainResult summary, full metrics dict for both
    candidates, the winning fitted pipeline) — caller decides whether
    to actually write the new model file based on result.promoted."""
    df = build_blended_dataset(synthetic_csv_path, real_examples)
    split = prepare_data(df)
    full_x = cap_infinite_feature(df, "seconds_since_last_llm_call")[list(SuggestionFeatures.FEATURE_NAMES)]
    full_y = df["worth_flagging"]

    results = {}
    fitted_pipelines = {}
    for model_name in CANDIDATE_MODELS:
        cv_pipeline = build_pipeline(model_name)
        cv_result = cross_validate_model(cv_pipeline, full_x, full_y, model_name)

        train_pipeline = build_pipeline(model_name)
        fitted = train_model(train_pipeline, split)
        test_result = evaluate_model(fitted, split.x_test, split.y_test, model_name)

        results[model_name] = {"cross_validation": cv_result.to_dict(), "test_set": test_result.to_dict()}
        fitted_pipelines[model_name] = fitted

    winner = max(CANDIDATE_MODELS, key=lambda m: results[m]["test_set"]["f1"])
    new_f1 = results[winner]["test_set"]["f1"]
    previous_f1 = load_previous_best_f1(previous_metrics_path)

    promoted = previous_f1 is None or new_f1 >= previous_f1

    summary = RetrainResult(
        winner=winner, new_f1=new_f1, previous_f1=previous_f1, promoted=promoted,
        real_examples_used=len(real_examples), synthetic_examples_used=len(df) - len(real_examples) * REAL_EXAMPLE_DUPLICATION_WEIGHT,
    )
    return summary, results, fitted_pipelines[winner]