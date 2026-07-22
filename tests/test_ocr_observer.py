from cogn_os.ocr.engine import OcrResult
from cogn_os.ocr.fake_engine import FakeOcrEngine
from cogn_os.plugins.ocr_observer import OcrObserver
from cogn_os.screenshot.fake_screenshotter import FakeScreenshotter
from cogn_os.screenshot.types import Screenshot


def make_screenshot(image_b64: str = "ZmFrZQ==") -> Screenshot:  # base64 for "fake"
    return Screenshot.now(image_b64=image_b64, width=100, height=100)


def test_produces_event_for_meaningful_text():
    screenshotter = FakeScreenshotter(screenshot=make_screenshot())
    ocr = FakeOcrEngine(text="ModuleNotFoundError: No module named requests", mean_confidence=85.0)
    observer = OcrObserver(screenshotter, ocr)

    events = observer.poll()

    assert len(events) == 1
    assert events[0].source == "ocr"
    assert events[0].event_type == "screen_text_detected"
    assert "ModuleNotFoundError" in events[0].payload["text"]
    assert events[0].confidence == 85.0


def test_no_screenshot_produces_no_event():
    screenshotter = FakeScreenshotter(screenshot=None)
    ocr = FakeOcrEngine(text="some text that is long enough")
    observer = OcrObserver(screenshotter, ocr)

    assert observer.poll() == []
    assert ocr.call_count == 0  # OCR never even called without a screenshot


def test_short_text_is_filtered_as_noise():
    screenshotter = FakeScreenshotter(screenshot=make_screenshot())
    ocr = FakeOcrEngine(text="OK", mean_confidence=90.0)  # below MIN_TEXT_LENGTH
    observer = OcrObserver(screenshotter, ocr)

    assert observer.poll() == []


def test_low_confidence_text_is_filtered():
    screenshotter = FakeScreenshotter(screenshot=make_screenshot())
    ocr = FakeOcrEngine(text="this is long enough text to pass the length check", mean_confidence=10.0)
    observer = OcrObserver(screenshotter, ocr, min_confidence=50.0)

    assert observer.poll() == []


def test_identical_text_on_second_poll_is_deduplicated():
    screenshotter = FakeScreenshotter(screenshot=make_screenshot())
    ocr = FakeOcrEngine(text="this text does not change between polls", mean_confidence=90.0)
    observer = OcrObserver(screenshotter, ocr)

    first = observer.poll()
    second = observer.poll()

    assert len(first) == 1
    assert second == []  # deduplicated, same text as last time


def test_changed_text_produces_a_new_event():
    screenshotter = FakeScreenshotter(screenshot=make_screenshot())
    ocr = FakeOcrEngine(text="first meaningful piece of screen text", mean_confidence=90.0)
    observer = OcrObserver(screenshotter, ocr)

    observer.poll()
    ocr.set_next("second, different piece of screen text", mean_confidence=90.0)
    events = observer.poll()

    assert len(events) == 1
    assert "second" in events[0].payload["text"]


def test_name_and_default_poll_interval():
    screenshotter = FakeScreenshotter(screenshot=None)
    ocr = FakeOcrEngine()
    observer = OcrObserver(screenshotter, ocr)

    assert observer.name == "ocr"
    assert observer.poll_interval_seconds == 15.0


def test_screenshotter_exception_does_not_crash_poll():
    class RaisingScreenshotter:
        def capture(self):
            raise RuntimeError("screen capture failed")

    observer = OcrObserver(RaisingScreenshotter(), FakeOcrEngine())
    events = observer.poll()  # must not raise

    assert events == []