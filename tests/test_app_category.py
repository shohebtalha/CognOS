from cogn_os.ml.app_category import AppCategory, categorize


def test_known_ide_is_categorized():
    assert categorize("code.exe") == AppCategory.IDE


def test_known_browser_is_categorized():
    assert categorize("chrome.exe") == AppCategory.BROWSER


def test_lookup_is_case_insensitive():
    assert categorize("Code.EXE") == AppCategory.IDE


def test_lookup_strips_whitespace():
    assert categorize("  code.exe  ") == AppCategory.IDE


def test_unknown_app_falls_back_to_other():
    assert categorize("some_random_app.exe") == AppCategory.OTHER


def test_empty_string_falls_back_to_other():
    assert categorize("") == AppCategory.OTHER