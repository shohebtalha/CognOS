from cogn_os.ml.app_category import AppCategory
from cogn_os.ml.features import SuggestionFeatures


def make_features(**overrides) -> SuggestionFeatures:
    defaults = dict(
        seconds_since_last_llm_call=120.0,
        hour_of_day=14,
        is_weekend=False,
        app_category=AppCategory.IDE,
        title_length=25,
        app_changed=True,
        is_first_time_app_today=False,
        switches_last_5min=3,
        title_semantic_similarity_to_previous=0.5,

    )
    defaults.update(overrides)
    return SuggestionFeatures(**defaults)


def test_to_dict_excludes_feature_names_constant():
    f = make_features()
    d = f.to_dict()
    assert "FEATURE_NAMES" not in d
    assert d["hour_of_day"] == 14


def test_to_dict_includes_all_real_fields():
    f = make_features()
    d = f.to_dict()
    assert set(d.keys()) == set(SuggestionFeatures.FEATURE_NAMES)


def test_is_frozen():
    f = make_features()
    try:
        f.hour_of_day = 0  # type: ignore[misc]
        assert False, "expected FrozenInstanceError"
    except AttributeError:
        pass