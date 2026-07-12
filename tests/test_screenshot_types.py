from datetime import timezone

from cogn_os.screenshot.types import Screenshot


def test_screenshot_now_sets_utc_timestamp_and_defaults():
    shot = Screenshot.now(image_b64="abc123", width=800, height=600)
    assert shot.image_b64 == "abc123"
    assert shot.width == 800
    assert shot.height == 600
    assert shot.format == "jpeg"
    assert shot.captured_at.tzinfo == timezone.utc


def test_screenshot_is_frozen():
    shot = Screenshot.now(image_b64="x", width=1, height=1)
    try:
        shot.width = 999  # type: ignore[misc]
        assert False, "expected FrozenInstanceError"
    except AttributeError:
        pass


def test_screenshot_supports_custom_format():
    shot = Screenshot.now(image_b64="x", width=1, height=1, format="png")
    assert shot.format == "png"