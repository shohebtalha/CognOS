from datetime import datetime, timezone

from cogn_os.capture.types import WindowInfo
from cogn_os.context.builder import build_context_summary


def w(app: str, title: str) -> WindowInfo:
    return WindowInfo(app_name=app, window_title=title, captured_at=datetime.now(timezone.utc))


def test_empty_history_returns_clear_message():
    current = w("code.exe", "main.py")
    summary = build_context_summary([], current)
    assert "no prior activity" in summary.lower()


def test_includes_real_history_entries():
    history = [w("chrome.exe", "Stack Overflow"), w("code.exe", "main.py")]
    current = w("code.exe", "utils.py")
    summary = build_context_summary(history, current)
    assert "chrome.exe" in summary
    assert "Stack Overflow" in summary
    assert "code.exe" in summary


def test_limits_to_max_history_lines():
    history = [w(f"app{i}.exe", f"title{i}") for i in range(20)]
    current = w("code.exe", "main.py")
    summary = build_context_summary(history, current)
    # only the most recent MAX_HISTORY_LINES should appear
    assert "app19.exe" in summary  # most recent
    assert "app0.exe" not in summary  # oldest, trimmed


def test_skips_entries_with_empty_titles():
    history = [w("explorer.exe", ""), w("code.exe", "main.py")]
    current = w("code.exe", "utils.py")
    summary = build_context_summary(history, current)
    assert "code.exe" in summary
    assert "main.py" in summary
    # explorer.exe entry with blank title shouldn't appear as a bare "- explorer.exe: "
    assert "- explorer.exe: \n" not in summary


def test_all_blank_titles_returns_clear_message():
    history = [w("explorer.exe", ""), w("explorer.exe", "")]
    current = w("code.exe", "main.py")
    summary = build_context_summary(history, current)
    assert "no prior activity" in summary.lower()


def test_summary_does_not_include_current_event_itself():
    history = [w("chrome.exe", "old page")]
    current = w("code.exe", "main.py")
    summary = build_context_summary(history, current)
    assert "main.py" not in summary  # current isn't part of history param