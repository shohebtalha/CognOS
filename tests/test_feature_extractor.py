from datetime import datetime, timedelta, timezone

from cogn_os.capture.types import WindowInfo
from cogn_os.ml.app_category import AppCategory
from cogn_os.ml.feature_extractor import FeatureExtractor

from cogn_os.embeddings.change_detector import SemanticChangeDetector
from cogn_os.embeddings.fake_provider import FakeEmbeddingProvider


def w(app_name: str, title: str, minutes_ago: float, base: datetime) -> WindowInfo:
    return WindowInfo(
        app_name=app_name,
        window_title=title,
        captured_at=base - timedelta(minutes=minutes_ago),
    )


def test_extract_computes_seconds_since_last_llm_call():
    base = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)  # a Monday
    current = w("code.exe", "main.py", 0, base)
    last_call = base - timedelta(seconds=90)

    extractor = FeatureExtractor()
    features = extractor.extract(current, None, [], last_call, set())

    assert features.seconds_since_last_llm_call == 90.0


def test_extract_returns_infinity_when_never_called():
    base = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)
    current = w("code.exe", "main.py", 0, base)

    extractor = FeatureExtractor()
    features = extractor.extract(current, None, [], None, set())

    assert features.seconds_since_last_llm_call == float("inf")


def test_extract_detects_app_changed():
    base = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)
    previous = w("chrome.exe", "docs", 1, base)
    current = w("code.exe", "main.py", 0, base)

    extractor = FeatureExtractor()
    features = extractor.extract(current, previous, [], None, set())

    assert features.app_changed is True


def test_extract_detects_no_app_change_on_title_only_change():
    base = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)
    previous = w("code.exe", "old.py", 1, base)
    current = w("code.exe", "new.py", 0, base)

    extractor = FeatureExtractor()
    features = extractor.extract(current, previous, [], None, set())

    assert features.app_changed is False


def test_extract_first_event_counts_as_app_changed():
    base = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)
    current = w("code.exe", "main.py", 0, base)

    extractor = FeatureExtractor()
    features = extractor.extract(current, None, [], None, set())

    assert features.app_changed is True


def test_extract_categorizes_app():
    base = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)
    current = w("chrome.exe", "some page", 0, base)

    extractor = FeatureExtractor()
    features = extractor.extract(current, None, [], None, set())

    assert features.app_category == AppCategory.BROWSER


def test_extract_novelty_flag_true_when_app_not_seen_today():
    base = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)
    current = w("slack.exe", "general", 0, base)

    extractor = FeatureExtractor()
    features = extractor.extract(current, None, [], None, apps_seen_today={"code.exe"})

    assert features.is_first_time_app_today is True


def test_extract_novelty_flag_false_when_app_already_seen_today():
    base = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)
    current = w("slack.exe", "general", 0, base)

    extractor = FeatureExtractor()
    features = extractor.extract(current, None, [], None, apps_seen_today={"slack.exe"})

    assert features.is_first_time_app_today is False


def test_extract_counts_switches_within_rolling_window():
    base = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)
    current = w("code.exe", "main.py", 0, base)
    history = [
        w("chrome.exe", "a", 1, base),   # 1 min ago — inside 5-min window
        w("slack.exe", "b", 3, base),    # 3 min ago — inside
        w("code.exe", "c", 10, base),    # 10 min ago — outside 5-min window
    ]

    extractor = FeatureExtractor(rolling_window=timedelta(minutes=5))
    features = extractor.extract(current, None, history, None, set())

    assert features.switches_last_5min == 2


def test_extract_weekend_flag():
    saturday = datetime(2026, 7, 11, 14, 0, tzinfo=timezone.utc)  # confirmed Saturday
    current = w("code.exe", "main.py", 0, saturday)

    extractor = FeatureExtractor()
    features = extractor.extract(current, None, [], None, set())

    assert features.is_weekend is True



def test_extract_without_change_detector_uses_neutral_default():
    base = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)
    current = w("code.exe", "main.py", 0, base)

    extractor = FeatureExtractor()  # no change_detector passed
    features = extractor.extract(current, None, [], None, set())

    assert features.title_semantic_similarity_to_previous == 0.5


def test_extract_with_change_detector_computes_real_similarity():
    base = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)
    previous = w("code.exe", "main.py", 1, base)
    current = w("code.exe", "main.py", 0, base)  # identical title

    detector = SemanticChangeDetector(FakeEmbeddingProvider())
    extractor = FeatureExtractor(change_detector=detector)
    features = extractor.extract(current, previous, [], None, set())

    assert features.title_semantic_similarity_to_previous == 1.0  # identical strings short-circuit to 1.0


def test_extract_first_event_similarity_is_zero_no_previous_title():
    base = datetime(2026, 7, 13, 14, 0, tzinfo=timezone.utc)
    current = w("code.exe", "main.py", 0, base)

    detector = SemanticChangeDetector(FakeEmbeddingProvider())
    extractor = FeatureExtractor(change_detector=detector)
    features = extractor.extract(current, None, [], None, set())

    assert features.title_semantic_similarity_to_previous == 0.0  # ChangeDecision default for no-previous case