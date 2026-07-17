import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # scripts/ isn't a package on the path by default

from scripts.generate_training_data import build_dataset  # noqa: E402


def test_dataset_generation_is_deterministic_with_fixed_seed():
    rows_a = build_dataset(num_sessions=3, events_per_session=20, seed=1)
    rows_b = build_dataset(num_sessions=3, events_per_session=20, seed=1)
    assert rows_a == rows_b


def test_different_seeds_produce_different_data():
    rows_a = build_dataset(num_sessions=3, events_per_session=20, seed=1)
    rows_b = build_dataset(num_sessions=3, events_per_session=20, seed=2)
    assert rows_a != rows_b


def test_dataset_has_both_classes_present():
    rows = build_dataset(num_sessions=10, events_per_session=50, seed=42)
    labels = {r["worth_flagging"] for r in rows}
    assert labels == {0, 1}


def test_positive_rate_is_realistic_not_extreme():
    # Guards against a labeling-logic regression that would make the
    # dataset trivial (near-0% or near-100% positive) and useless for
    # training a meaningful classifier.
    rows = build_dataset(num_sessions=20, events_per_session=60, seed=42)
    positive_rate = sum(r["worth_flagging"] for r in rows) / len(rows)
    assert 0.05 < positive_rate < 0.40


def test_row_count_matches_sessions_times_events():
    rows = build_dataset(num_sessions=5, events_per_session=30, seed=1)
    assert len(rows) == 5 * 30


def test_every_row_has_all_expected_columns():
    rows = build_dataset(num_sessions=1, events_per_session=10, seed=1)
    expected_cols = {
        "seconds_since_last_llm_call", "hour_of_day", "is_weekend",
        "app_category", "title_length", "app_changed",
        "is_first_time_app_today", "switches_last_5min", "worth_flagging",
        "title_semantic_similarity_to_previous",

    }
    assert set(rows[0].keys()) == expected_cols