"""
These run against the *actual* Day 6 trained model file — a deliberate
choice: this is the one place where testing against the real artifact
(not a mock) matters, since it's what proves the feature-name/dtype
contract between training and inference genuinely lines up, not just
in theory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cogn_os.ml.app_category import AppCategory
from cogn_os.ml.features import SuggestionFeatures
from cogn_os.ml.model_suggestion_gate import ModelSuggestionGate

MODEL_PATH = Path(__file__).parent.parent / "models" / "suggestion_classifier.joblib"


@pytest.fixture
def gate():
    if not MODEL_PATH.exists():
        pytest.skip("trained model not present — run scripts/train_classifier.py first")
    return ModelSuggestionGate(model_path=MODEL_PATH)


def make_features(**overrides) -> SuggestionFeatures:
    defaults = dict(
        seconds_since_last_llm_call=60.0,
        hour_of_day=10,
        is_weekend=False,
        app_category=AppCategory.IDE,
        title_length=20,
        app_changed=True,
        is_first_time_app_today=False,
        switches_last_5min=1,
    )
    defaults.update(overrides)
    return SuggestionFeatures(**defaults)


def test_should_flag_returns_a_bool(gate):
    result = gate.should_flag(make_features())
    assert isinstance(result, bool)


def test_should_flag_does_not_crash_on_extreme_values(gate):
    extreme = make_features(
        seconds_since_last_llm_call=999999.0,
        switches_last_5min=999,
        title_length=0,
    )
    result = gate.should_flag(extreme)
    assert isinstance(result, bool)


def test_missing_model_file_raises_clear_error(tmp_path):
    fake_path = tmp_path / "does_not_exist.joblib"
    with pytest.raises(RuntimeError, match="No trained model found"):
        ModelSuggestionGate(model_path=fake_path)


def test_threshold_is_configurable(gate):
    # A near-0 threshold should flag almost everything; a near-1
    # threshold should flag almost nothing — for the *same* features.
    features = make_features()
    lenient_gate = ModelSuggestionGate(model_path=MODEL_PATH, threshold=0.01)
    strict_gate = ModelSuggestionGate(model_path=MODEL_PATH, threshold=0.99)

    assert lenient_gate.should_flag(features) is True
    assert strict_gate.should_flag(features) is False