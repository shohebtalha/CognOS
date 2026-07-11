from cogn_os.capture.types import WindowInfo
from cogn_os.service.filters import is_excluded


def test_excluded_app_is_filtered():
    info = WindowInfo.now("LockApp.exe", "Lock Screen")
    assert is_excluded(info, frozenset({"LockApp.exe"})) is True


def test_non_excluded_app_passes():
    info = WindowInfo.now("code.exe", "main.py")
    assert is_excluded(info, frozenset({"LockApp.exe"})) is False


def test_match_is_case_insensitive():
    info = WindowInfo.now("LOCKAPP.EXE", "Lock Screen")
    assert is_excluded(info, frozenset({"lockapp.exe"})) is True


def test_empty_exclusion_set_excludes_nothing():
    info = WindowInfo.now("anything.exe", "t")
    assert is_excluded(info, frozenset()) is False