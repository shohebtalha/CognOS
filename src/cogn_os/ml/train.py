"""
Builds and trains the suggestion-worthiness classifier.

Two model families compared, not just one — LogisticRegression as an
interpretable baseline, RandomForestClassifier as a comparison — because
"I trained a model" is a weaker claim than "I compared models and chose
based on measured performance." Whichever wins on held-out F1 gets
saved as the production model.

sklearn's ColumnTransformer + Pipeline keeps preprocessing (scaling
numeric features, one-hot encoding the categorical app_category) and
the model itself as one serializable unit — so inference code (Day 7)
never has to remember to replicate preprocessing steps separately,
which is one of the most common sources of train/serve skew.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from cogn_os.ml.dataset import cap_infinite_feature
from cogn_os.ml.features import SuggestionFeatures

NUMERIC_FEATURES = [
    "seconds_since_last_llm_call", "hour_of_day", "title_length", "switches_last_5min",
]
BOOLEAN_FEATURES = ["is_weekend", "app_changed", "is_first_time_app_today"]
CATEGORICAL_FEATURES = ["app_category"]
LABEL_COLUMN = "worth_flagging"


def _build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), NUMERIC_FEATURES + BOOLEAN_FEATURES),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )


def build_pipeline(model_name: str) -> Pipeline:
    if model_name == "logistic_regression":
        model = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    elif model_name == "random_forest":
        model = RandomForestClassifier(
            n_estimators=200, max_depth=8, class_weight="balanced", random_state=42
        )
    else:
        raise ValueError(f"unknown model_name: {model_name}")

    return Pipeline(steps=[("preprocess", _build_preprocessor()), ("model", model)])


@dataclass(frozen=True)
class TrainTestSplit:
    x_train: pd.DataFrame
    x_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series


def prepare_data(df: pd.DataFrame, test_size: float = 0.2, seed: int = 42) -> TrainTestSplit:
    df = cap_infinite_feature(df, "seconds_since_last_llm_call")
    feature_cols = list(SuggestionFeatures.FEATURE_NAMES)
    x = df[feature_cols]
    y = df[LABEL_COLUMN]

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=test_size, random_state=seed, stratify=y
    )
    return TrainTestSplit(x_train=x_train, x_test=x_test, y_train=y_train, y_test=y_test)


def train_model(pipeline: Pipeline, split: TrainTestSplit) -> Pipeline:
    pipeline.fit(split.x_train, split.y_train)
    return pipeline