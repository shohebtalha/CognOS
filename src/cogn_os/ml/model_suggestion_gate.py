"""
Real SuggestionGate backed by the trained scikit-learn pipeline from
Day 6. Loads the .joblib file once at construction (not per-call —
joblib.load is relatively expensive and the model is immutable during
a run). Converts a single SuggestionFeatures into the one-row DataFrame
shape the pipeline expects, using the exact column order/names defined
in SuggestionFeatures.FEATURE_NAMES — the same shared contract used at
training time, which is precisely what prevents train/serve skew here.
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import pandas as pd

from cogn_os.ml.features import SuggestionFeatures
from cogn_os.ml.suggestion_gate import SuggestionGate

logger = logging.getLogger(__name__)


class ModelSuggestionGate(SuggestionGate):
    def __init__(self, model_path: Path, threshold: float = 0.5) -> None:
        self._threshold = threshold
        try:
            self._pipeline = joblib.load(model_path)
        except FileNotFoundError:
            raise RuntimeError(
                f"No trained model found at {model_path}. Run "
                f"'python scripts/train_classifier.py' first."
            )

    def should_flag(self, features: SuggestionFeatures) -> bool:
        row = {name: getattr(features, name) for name in SuggestionFeatures.FEATURE_NAMES}
        # app_category is an enum on the dataclass but the pipeline was
        # trained on its string .value (see dataset.py/train.py) — this
        # conversion must exactly mirror what generate_training_data.py did.
        row["app_category"] = row["app_category"].value if hasattr(row["app_category"], "value") else row["app_category"]

        x = pd.DataFrame([row])

        try:
            probability = self._pipeline.predict_proba(x)[0][1]  # P(class=1)
            return bool(probability >= self._threshold)
        except Exception:
            logger.exception("SuggestionGate inference failed; defaulting to False")
            return False