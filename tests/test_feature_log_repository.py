from cogn_os.capture.types import WindowInfo
from cogn_os.storage.sqlalchemy_repository import SqlAlchemyFeatureLogRepository

SAMPLE_FEATURES = {
    "seconds_since_last_llm_call": 60.0, "hour_of_day": 10, "is_weekend": False,
    "app_category": "ide", "title_length": 20, "app_changed": True,
    "is_first_time_app_today": True, "switches_last_5min": 2,
}


def test_add_returns_assigned_id(sqlite_session_factory):
    repo = SqlAlchemyFeatureLogRepository(sqlite_session_factory)
    info = WindowInfo.now("code.exe", "main.py")

    log_id = repo.add(info, SAMPLE_FEATURES, probability=0.62, flagged=True)

    assert isinstance(log_id, int)


def test_new_entry_has_no_label_by_default(sqlite_session_factory):
    repo = SqlAlchemyFeatureLogRepository(sqlite_session_factory)
    info = WindowInfo.now("code.exe", "main.py")
    log_id = repo.add(info, SAMPLE_FEATURES, probability=0.62, flagged=True)

    unlabeled = repo.recent_unlabeled(limit=10)

    assert len(unlabeled) == 1
    assert unlabeled[0].id == log_id
    assert unlabeled[0].user_label is None


def test_set_label_moves_entry_out_of_unlabeled(sqlite_session_factory):
    repo = SqlAlchemyFeatureLogRepository(sqlite_session_factory)
    info = WindowInfo.now("code.exe", "main.py")
    log_id = repo.add(info, SAMPLE_FEATURES, probability=0.62, flagged=True)

    success = repo.set_label(log_id, 1)

    assert success is True
    assert repo.recent_unlabeled() == []
    assert len(repo.labeled_examples()) == 1
    assert repo.labeled_examples()[0].user_label == 1


def test_set_label_on_nonexistent_id_returns_false(sqlite_session_factory):
    repo = SqlAlchemyFeatureLogRepository(sqlite_session_factory)
    assert repo.set_label(99999, 1) is False


def test_labeled_examples_preserves_feature_values(sqlite_session_factory):
    repo = SqlAlchemyFeatureLogRepository(sqlite_session_factory)
    info = WindowInfo.now("slack.exe", "general")
    log_id = repo.add(info, SAMPLE_FEATURES, probability=0.5, flagged=False)
    repo.set_label(log_id, 0)

    examples = repo.labeled_examples()

    assert examples[0].features["app_category"] == "ide"
    assert examples[0].features["switches_last_5min"] == 2


def test_recent_unlabeled_respects_limit(sqlite_session_factory):
    repo = SqlAlchemyFeatureLogRepository(sqlite_session_factory)
    for i in range(5):
        repo.add(WindowInfo.now(f"app{i}.exe", "t"), SAMPLE_FEATURES, probability=0.5, flagged=False)

    assert len(repo.recent_unlabeled(limit=3)) == 3