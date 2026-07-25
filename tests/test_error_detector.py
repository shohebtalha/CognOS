from cogn_os.ocr.error_detector import contains_error_signal


def test_detects_python_traceback():
    assert contains_error_signal("Traceback (most recent call last):\nSyntaxError: invalid syntax")


def test_ignores_plain_text():
    assert not contains_error_signal("Writing a calm project status update")
