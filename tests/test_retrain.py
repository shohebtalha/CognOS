from pathlib import Path

import pandas as pd
import pytest

from cogn_os.ml.retrain import (
    build_blended_dataset, load_previous_best_f1, real_logs_to_dataframe,
)


class FakeFeatureLogDTO:
    def __init__(self, features: dict, label: int) -> None:
        self.features = features
        self.user_label = label


def make_example(label: int) -> FakeFeatureLogDTO:
    return FakeFeatureLogDTO(
        features={
            "seconds_since_last_llm_call": 60.0, "hour_of_day": 10, "is_weekend": False,
            "app_category": "ide", "title_length": 20, "app_changed": True,
            "is_first_time_app_today": True, "switches_last_5min": 2,
        },
        label=label,
    )


def test_real_logs_to_dataframe_empty_list_returns_empty_df_with_correct_columns():
    df = real_logs_to_dataframe([])
    assert len(df) == 0
    assert "worth_flagging" in df.columns


def test_real_logs_to_dataframe_preserves_labels():
    examples = [make_example(1), make_example(0)]
    df = real_logs_to_dataframe(examples)
    assert list(df["worth_flagging"]) == [1, 0]


def test_build_blended_dataset_with_no_real_examples_equals_synthetic_only(tmp_path):
    csv_path = tmp_path / "synthetic.csv"
    csv_path.write_text(
        "seconds_since_last_llm_call,hour_of_day,is_weekend,app_category,"
        "title_length,app_changed,is_first_time_app_today,switches_last_5min,worth_flagging\n"
        "inf,9,False,browser,29,True,True,0,0\n"
    )
    blended = build_blended_dataset(csv_path, real_examples=[])
    assert len(blended) == 1


def test_build_blended_dataset_duplicates_real_examples_by_weight(tmp_path):
    csv_path = tmp_path / "synthetic.csv"
    csv_path.write_text(
        "seconds_since_last_llm_call,hour_of_day,is_weekend,app_category,"
        "title_length,app_changed,is_first_time_app_today,switches_last_5min,worth_flagging\n"
        "inf,9,False,browser,29,True,True,0,0\n"
    )
    real_examples = [make_example(1)]
    blended = build_blended_dataset(csv_path, real_examples)
    # 1 synthetic row + (1 real row * duplication weight of 5) = 6
    assert len(blended) == 6


def test_load_previous_best_f1_returns_none_if_file_missing(tmp_path):
    missing = tmp_path / "does_not_exist.json"
    assert load_previous_best_f1(missing) is None


def test_load_previous_best_f1_reads_winner_f1(tmp_path):
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        '{"winner": "random_forest", "results": {"random_forest": {"test_set": {"f1": 0.5116}}}}'
    )
    assert load_previous_best_f1(metrics_path) == 0.5116