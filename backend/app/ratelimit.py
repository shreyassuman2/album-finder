"""A minimal rate limiter: guarantees calls are spaced at least N seconds apart."""

import threading
import time


class RateLimiter:
    def __init__(self, min_interval: float, clock=time.monotonic, sleep=time.sleep):
        # clock and sleep are parameters only so tests can fake time.
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._next_allowed = 0.0
        # The lock matters once FastAPI runs requests on several threads:
        # without it, two threads could both see "OK to go" at the same moment.
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Block until it's OK to make the next request, then reserve that slot."""
        with self._lock:
            now = self._clock()
            if now < self._next_allowed:
                self._sleep(self._next_allowed - now)
                now = self._next_allowed
            self._next_allowed = now + self.min_interval
