"""
Loads the training CSV into a properly-typed pandas DataFrame. CSV
round-trips every value as a string, including 'inf' and 'True'/'False'
— pandas' automatic dtype inference does NOT reliably parse 'inf' as
float infinity in all pandas versions, so every column gets an explicit
converter here rather than relying on inference. This is the one place
that must agree with generate_training_data.py's output schema; if that
schema changes, this is the only file that needs updating too.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BOOL_COLUMNS = ["is_weekend", "app_changed", "is_first_time_app_today"]
INT_COLUMNS = ["hour_of_day", "title_length", "switches_last_5min", "worth_flagging"]
FLOAT_COLUMNS = ["seconds_since_last_llm_call"]
CATEGORICAL_COLUMNS = ["app_category"]


def _parse_bool(series: pd.Series) -> pd.Series:
    return series.map({"True": True, "False": False, True: True, False: False}).astype(bool)


def load_dataset(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype=str)

    for col in BOOL_COLUMNS:
        df[col] = _parse_bool(df[col])

    for col in INT_COLUMNS:
        df[col] = df[col].astype(int)

    for col in FLOAT_COLUMNS:
        # explicit inf handling: 'inf' string -> float('inf'), everything
        # else parsed normally. Cap at a large finite value afterward
        # (see cap_infinite_feature) since most models handle large
        # finite numbers better than literal infinity.
        df[col] = df[col].replace("inf", "Infinity").astype(float)

    for col in CATEGORICAL_COLUMNS:
        df[col] = df[col].astype("category")

    return df


def cap_infinite_feature(df: pd.DataFrame, column: str, cap_value: float = 3600.0) -> pd.DataFrame:
    """Replace +inf with a large finite cap (default: 1 hour in seconds).
    Tree/linear models generally handle large finite numbers far more
    predictably than literal infinity, which can silently break scaling
    (StandardScaler) or split logic in some implementations."""
    df = df.copy()
    df[column] = df[column].replace([float("inf")], cap_value)
    return df

def cap_feature(df: pd.DataFrame, column: str, cap_value: float) -> pd.DataFrame:
    """Generic version of cap_infinite_feature — clips any feature to a
    max value, not just infinity. Prevents linear models from
    extrapolating wildly on feature values far outside the training
    distribution (e.g. switches_last_5min hitting values never seen
    during training), which was observed to saturate predict_proba to
    exactly 1.0 during live testing."""
    df = df.copy()
    df[column] = df[column].clip(upper=cap_value)
    return df

