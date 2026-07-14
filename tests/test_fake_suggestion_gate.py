from cogn_os.ml.app_category import AppCategory
from cogn_os.ml.fake_suggestion_gate import FakeSuggestionGate
from cogn_os.ml.features import SuggestionFeatures


def make_features() -> SuggestionFeatures:
    return SuggestionFeatures(
        seconds_since_last_llm_call=10.0, hour_of_day=9, is_weekend=False,
        app_category=AppCategory.IDE, title_length=5, app_changed=True,
        is_first_time_app_today=False, switches_last_5min=0,
    )


def test_fixed_value_always_returned():
    gate = FakeSuggestionGate(sequence=True)
    assert gate.should_flag(make_features()) is True
    assert gate.should_flag(make_features()) is True


def test_sequence_played_back_in_order():
    gate = FakeSuggestionGate(sequence=[True, False, True])
    assert gate.should_flag(make_features()) is True
    assert gate.should_flag(make_features()) is False
    assert gate.should_flag(make_features()) is True


def test_records_received_features():
    gate = FakeSuggestionGate(sequence=True)
    f = make_features()
    gate.should_flag(f)
    assert gate.received_features == [f]


def test_empty_sequence_defaults_to_false():
    gate = FakeSuggestionGate(sequence=[])
    assert gate.should_flag(make_features()) is False