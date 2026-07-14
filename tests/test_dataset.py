import pandas as pd
import pytest

from cogn_os.ml.dataset import cap_infinite_feature, load_dataset


@pytest.fixture
def sample_csv(tmp_path):
    path = tmp_path / "sample.csv"
    path.write_text(
        "seconds_since_last_llm_call,hour_of_day,is_weekend,app_category,"
        "title_length,app_changed,is_first_time_app_today,switches_last_5min,worth_flagging\n"
        "inf,9,False,browser,29,True,True,0,0\n"
        "120.5,14,True,ide,15,False,False,3,1\n"
    )
    return path


def test_load_dataset_parses_infinity(sample_csv):
    df = load_dataset(sample_csv)
    assert df.loc[0, "seconds_since_last_llm_call"] == float("inf")


def test_load_dataset_parses_bools_correctly(sample_csv):
    df = load_dataset(sample_csv)
    assert df.loc[0, "is_weekend"] == False  # noqa: E712
    assert df.loc[1, "is_weekend"] == True  # noqa: E712
    assert df["is_weekend"].dtype == bool


def test_load_dataset_parses_ints(sample_csv):
    df = load_dataset(sample_csv)
    assert df.loc[0, "hour_of_day"] == 9
    assert df.loc[0, "switches_last_5min"] == 0
    assert pd.api.types.is_integer_dtype(df["hour_of_day"])


def test_load_dataset_keeps_category_as_categorical(sample_csv):
    df = load_dataset(sample_csv)
    assert df["app_category"].dtype.name == "category"


def test_cap_infinite_feature_replaces_inf_with_cap():
    df = pd.DataFrame({"x": [float("inf"), 50.0, float("inf")]})
    capped = cap_infinite_feature(df, "x", cap_value=999.0)
    assert list(capped["x"]) == [999.0, 50.0, 999.0]


def test_cap_infinite_feature_does_not_mutate_original():
    df = pd.DataFrame({"x": [float("inf")]})
    cap_infinite_feature(df, "x", cap_value=999.0)
    assert df.loc[0, "x"] == float("inf")  # original untouched