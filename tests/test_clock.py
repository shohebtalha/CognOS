from cogn_os.service.clock import FakeClock


def test_fake_clock_starts_at_given_time():
    clock = FakeClock(start=100.0)
    assert clock.now() == 100.0


def test_fake_clock_sleep_advances_time():
    clock = FakeClock(start=0.0)
    clock.sleep(5.0)
    assert clock.now() == 5.0


def test_fake_clock_records_sleep_calls():
    clock = FakeClock()
    clock.sleep(3.0)
    clock.sleep(2.0)
    assert clock.sleep_calls == [3.0, 2.0]


def test_fake_clock_advance_does_not_record_as_sleep():
    clock = FakeClock()
    clock.advance(10.0)
    assert clock.now() == 10.0
    assert clock.sleep_calls == []