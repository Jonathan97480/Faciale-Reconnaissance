import threading
import time
from collections import deque


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = {}

    def check(self, bucket: str, limit: int, window_seconds: float) -> tuple[bool, float]:
        now = time.monotonic()
        with self._lock:
            entries = self._buckets.setdefault(bucket, deque())
            cutoff = now - window_seconds
            while entries and entries[0] <= cutoff:
                entries.popleft()

            if len(entries) >= limit:
                retry_after = max(0.0, window_seconds - (now - entries[0]))
                return False, retry_after

            entries.append(now)
            return True, 0.0

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


production_rate_limiter = InMemoryRateLimiter()
