from cogn_os.screenshot.fake_screenshotter import FakeScreenshotter
from cogn_os.screenshot.types import Screenshot


def test_returns_configured_screenshot():
    shot = Screenshot.now("abc", 100, 100)
    fake = FakeScreenshotter(screenshot=shot)

    assert fake.capture() is shot
    assert fake.call_count == 1


def test_returns_none_by_default():
    fake = FakeScreenshotter()
    assert fake.capture() is None


def test_set_next_changes_subsequent_captures():
    shot1 = Screenshot.now("a", 1, 1)
    shot2 = Screenshot.now("b", 2, 2)
    fake = FakeScreenshotter(screenshot=shot1)

    assert fake.capture() is shot1
    fake.set_next(shot2)
    assert fake.capture() is shot2
    assert fake.call_count == 2