import pytest

from app.ratelimit import RateLimiter


class FakeTime:
    def __init__(self):
        self.now = 100.0
        self.slept = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def test_first_call_does_not_wait():
    t = FakeTime()
    RateLimiter(1.0, clock=t.clock, sleep=t.sleep).wait()
    assert t.slept == []


def test_back_to_back_calls_are_spaced_out():
    t = FakeTime()
    limiter = RateLimiter(1.0, clock=t.clock, sleep=t.sleep)
    limiter.wait()
    t.now += 0.3  # 0.3s of work happens between calls
    limiter.wait()
    assert t.slept == [pytest.approx(0.7)]


def test_no_wait_after_enough_time_passes():
    t = FakeTime()
    limiter = RateLimiter(1.0, clock=t.clock, sleep=t.sleep)
    limiter.wait()
    t.now += 5
    limiter.wait()
    assert t.slept == []
