import pandas as pd
import pytest

from cogn_os.ml.train import build_pipeline, prepare_data, train_model


@pytest.fixture
def toy_dataframe():
    rows = []
    for i in range(20):
        rows.append({
            "seconds_since_last_llm_call": float(i * 10),
            "hour_of_day": i % 24,
            "is_weekend": bool(i % 2),
            "app_category": "ide" if i % 3 == 0 else "browser",
            "title_length": 10 + i,
            "app_changed": bool(i % 2),
            "is_first_time_app_today": bool(i % 4 == 0),
            "switches_last_5min": i % 5,
            "title_semantic_similarity_to_previous": 0.5 + (i % 5) * 0.1,
            "worth_flagging": i % 2,
        })
    return pd.DataFrame(rows)


def test_build_pipeline_logistic_regression():
    pipeline = build_pipeline("logistic_regression")
    assert pipeline.named_steps["model"].__class__.__name__ == "LogisticRegression"


def test_build_pipeline_random_forest():
    pipeline = build_pipeline("random_forest")
    assert pipeline.named_steps["model"].__class__.__name__ == "RandomForestClassifier"


def test_build_pipeline_rejects_unknown_model():
    with pytest.raises(ValueError):
        build_pipeline("not_a_real_model")


def test_prepare_data_splits_correctly(toy_dataframe):
    split = prepare_data(toy_dataframe, test_size=0.3, seed=1)
    assert len(split.x_train) + len(split.x_test) == len(toy_dataframe)
    assert len(split.x_test) == pytest.approx(6, abs=1)  # ~30% of 20


def test_prepare_data_caps_infinite_values(toy_dataframe):
    toy_dataframe.loc[0, "seconds_since_last_llm_call"] = float("inf")
    split = prepare_data(toy_dataframe, test_size=0.3, seed=1)
    full = pd.concat([split.x_train, split.x_test])
    assert not (full["seconds_since_last_llm_call"] == float("inf")).any()


def test_train_model_produces_fitted_pipeline_that_can_predict(toy_dataframe):
    split = prepare_data(toy_dataframe, test_size=0.3, seed=1)
    pipeline = build_pipeline("logistic_regression")

    fitted = train_model(pipeline, split)
    predictions = fitted.predict(split.x_test)

    assert len(predictions) == len(split.x_test)
    assert set(predictions).issubset({0, 1})