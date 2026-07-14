"""
End-to-end training script: load data -> train both model candidates ->
cross-validate each -> evaluate on held-out test set -> save whichever
model wins on test-set F1, plus a metrics.json documenting both
candidates' numbers (not just the winner) for transparency.

Run: python scripts/train_classifier.py
Outputs:
  models/suggestion_classifier.joblib  (the winning pipeline)
  models/metrics.json                  (both models' CV + test metrics)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib

sys.path.insert(0, str(Path(__file__).parent.parent))

from cogn_os.ml.cross_validate import cross_validate_model  # noqa: E402
from cogn_os.ml.dataset import cap_infinite_feature, load_dataset  # noqa: E402
from cogn_os.ml.evaluate import evaluate_model  # noqa: E402
from cogn_os.ml.features import SuggestionFeatures  # noqa: E402
from cogn_os.ml.train import build_pipeline, prepare_data, train_model  # noqa: E402

DATA_PATH = Path(__file__).parent.parent / "data" / "synthetic_events.csv"
MODEL_OUT_PATH = Path(__file__).parent.parent / "models" / "suggestion_classifier.joblib"
METRICS_OUT_PATH = Path(__file__).parent.parent / "models" / "metrics.json"

CANDIDATE_MODELS = ["logistic_regression", "random_forest"]


def main() -> None:
    df = load_dataset(DATA_PATH)
    split = prepare_data(df)

    full_x = cap_infinite_feature(df, "seconds_since_last_llm_call")[list(SuggestionFeatures.FEATURE_NAMES)]
    full_y = df["worth_flagging"]

    results = {}
    fitted_pipelines = {}

    for model_name in CANDIDATE_MODELS:
        print(f"\n=== {model_name} ===")

        cv_pipeline = build_pipeline(model_name)
        cv_result = cross_validate_model(cv_pipeline, full_x, full_y, model_name)
        print(f"5-fold CV F1: {cv_result.mean} +/- {cv_result.std}")

        train_pipeline = build_pipeline(model_name)
        fitted = train_model(train_pipeline, split)
        test_result = evaluate_model(fitted, split.x_test, split.y_test, model_name)
        print(f"Test set — precision: {test_result.precision}, recall: {test_result.recall}, f1: {test_result.f1}")
        print(f"Confusion matrix — TN:{test_result.true_negatives} FP:{test_result.false_positives} "
              f"FN:{test_result.false_negatives} TP:{test_result.true_positives}")

        results[model_name] = {"cross_validation": cv_result.to_dict(), "test_set": test_result.to_dict()}
        fitted_pipelines[model_name] = fitted

    winner = max(CANDIDATE_MODELS, key=lambda m: results[m]["test_set"]["f1"])
    print(f"\n>>> Winner (by test-set F1): {winner}")

    MODEL_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(fitted_pipelines[winner], MODEL_OUT_PATH)

    metrics_report = {
        "winner": winner,
        "feature_names": list(SuggestionFeatures.FEATURE_NAMES),
        "dataset_size": len(df),
        "results": results,
    }
    METRICS_OUT_PATH.write_text(json.dumps(metrics_report, indent=2))
    print(f"\nSaved model to {MODEL_OUT_PATH}")
    print(f"Saved metrics to {METRICS_OUT_PATH}")


if __name__ == "__main__":
    main()