from datetime import datetime, timezone

from cogn_os.capture.types import WindowInfo
from cogn_os.context.privacy_filter import is_sensitive


def w(app: str, title: str) -> WindowInfo:
    return WindowInfo(app_name=app, window_title=title, captured_at=datetime.now(timezone.utc))


def test_banking_title_is_sensitive():
    assert is_sensitive(w("chrome.exe", "Bank of Example - Sign In")) is True


def test_password_manager_title_is_sensitive():
    assert is_sensitive(w("chrome.exe", "Vault - 1Password")) is True


def test_password_manager_app_name_is_sensitive():
    assert is_sensitive(w("1password.exe", "1Password")) is True


def test_normal_coding_title_is_not_sensitive():
    assert is_sensitive(w("code.exe", "main.py - Visual Studio Code")) is False


def test_case_insensitive_matching():
    assert is_sensitive(w("chrome.exe", "MY BANK ACCOUNT")) is True


def test_paypal_title_is_sensitive():
    assert is_sensitive(w("chrome.exe", "PayPal - Send Money")) is True


def test_tax_title_is_sensitive():
    assert is_sensitive(w("chrome.exe", "TurboTax - File Your Taxes")) is True


def test_unrelated_word_containing_substring_is_not_falsely_flagged():
    # "signing" contains "sign" but shouldn't false-positive on the
    # word-boundary-aware "sign.?in" pattern
    assert is_sensitive(w("code.exe", "signing_ceremony.py")) is False