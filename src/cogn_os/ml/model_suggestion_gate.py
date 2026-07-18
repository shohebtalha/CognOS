"""
Real SuggestionGate backed by the trained scikit-learn pipeline.
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import pandas as pd

from cogn_os.ml.dataset import cap_feature, cap_infinite_feature
from cogn_os.ml.features import SuggestionFeatures
from cogn_os.ml.suggestion_gate import SuggestionGate

logger = logging.getLogger(__name__)

SWITCHES_CAP = 6.0


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

    def _to_model_input(self, features: SuggestionFeatures) -> pd.DataFrame:
        """SINGLE shared preprocessing path for every caller (should_flag,
        predict_probability, any future method) — this replaces two
        previously-duplicated implementations, one of which (predict_probability)
        was missed when the switches_last_5min cap was added, causing live
        diagnostics to bypass the fix entirely while should_flag had it.
        Never duplicate this logic again; add new preprocessing steps here only."""
        row = {name: getattr(features, name) for name in SuggestionFeatures.FEATURE_NAMES}
        row["app_category"] = row["app_category"].value if hasattr(row["app_category"], "value") else row["app_category"]

        x = pd.DataFrame([row])
        x = cap_infinite_feature(x, "seconds_since_last_llm_call")
        x = cap_feature(x, "switches_last_5min", cap_value=SWITCHES_CAP)
        return x

    def should_flag(self, features: SuggestionFeatures) -> bool:
        x = self._to_model_input(features)
        try:
            probability = self._pipeline.predict_proba(x)[0][1]
            return bool(probability >= self._threshold)
        except Exception:
            logger.exception("SuggestionGate inference failed; defaulting to False")
            return False

    def predict_probability(self, features: SuggestionFeatures) -> float:
        """Same preprocessing as should_flag (via _to_model_input), returns
        the raw probability instead of the thresholded decision. Used by
        diagnose_gate.py — must never diverge from should_flag's preprocessing again."""
        x = self._to_model_input(features)
        return float(self._pipeline.predict_proba(x)[0][1])