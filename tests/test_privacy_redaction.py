from cogn_os.privacy import redact_payload, redact_text


def test_redact_text_removes_api_key():
    text = redact_text("api_key = 'abcdefghijklmnopqrstuvwxyz'")

    assert "abcdefghijklmnopqrstuvwxyz" not in text
    assert "[REDACTED]" in text


def test_redact_payload_recurses():
    payload = redact_payload({"nested": {"token": "Bearer abcdefghijklmnop"}})

    assert "abcdefghijklmnop" not in str(payload)
