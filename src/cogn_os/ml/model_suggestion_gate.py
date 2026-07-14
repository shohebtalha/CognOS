from __future__ import annotations

import logging
from pathlib import Path

import joblib
import pandas as pd

from cogn_os.ml.dataset import cap_infinite_feature
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
        row["app_category"] = row["app_category"].value if hasattr(row["app_category"], "value") else row["app_category"]

        x = pd.DataFrame([row])
        # Must mirror prepare_data()'s preprocessing exactly — the model
        # was trained on capped values, so live inference has to cap the
        # same way or infinity (e.g. the very first event of a session,
        # where seconds_since_last_llm_call is genuinely infinite) breaks
        # StandardScaler at predict time. This is exactly the train/serve
        # skew the shared SuggestionFeatures schema was meant to prevent
        # — the schema covered *names*, but not this one preprocessing step.
        x = cap_infinite_feature(x, "seconds_since_last_llm_call")

        try:
            probability = self._pipeline.predict_proba(x)[0][1]
            return bool(probability >= self._threshold)
        except Exception:
            logger.exception("SuggestionGate inference failed; defaulting to False")
            return False
        
    def predict_probability(self, features: SuggestionFeatures) -> float:
        """Same preprocessing as should_flag, but returns the raw
        probability instead of the thresholded decision. Useful for
        diagnostics/debugging — never used in the live capture path."""
        row = {name: getattr(features, name) for name in SuggestionFeatures.FEATURE_NAMES}
        row["app_category"] = row["app_category"].value if hasattr(row["app_category"], "value") else row["app_category"]

        x = pd.DataFrame([row])
        x = cap_infinite_feature(x, "seconds_since_last_llm_call")

        return float(self._pipeline.predict_proba(x)[0][1])