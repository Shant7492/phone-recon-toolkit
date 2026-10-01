"""Small in-memory limiters. Per-process: use Redis if you scale out."""
from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Callable, Deque, Dict, Tuple


class SlidingWindowLimiter:
    def __init__(self, limit: int, window: float, max_keys: int = 10_000,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.limit = limit
        self.window = window
        self.max_keys = max_keys
        self._clock = clock
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> Tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        if self.limit <= 0:
            return False, int(self.window)
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False, int(hits[0] + self.window - now) + 1
            hits.append(now)
            if len(self._hits) > self.max_keys:
                self._prune(now)
            return True, 0

    def _prune(self, now: float) -> None:
        stale = [k for k, q in self._hits.items()
                 if not q or q[-1] <= now - self.window]
        for key in stale:
            del self._hits[key]
        if len(self._hits) > self.max_keys:  # still too big: fail open
            self._hits.clear()


class DailyCounter:
    """Counts events per UTC day; resets automatically at midnight."""

    def __init__(self, cap: int) -> None:
        self.cap = cap
        self._day = self._today()
        self._count = 0
        self._lock = threading.Lock()

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def take(self) -> bool:
        with self._lock:
            today = self._today()
            if today != self._day:
                self._day, self._count = today, 0
            if self._count >= self.cap:
                return False
            self._count += 1
            return True
