from collections import deque
from threading import Lock
from time import monotonic


class LoginRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int, lockout_seconds: int):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._attempts: dict[str, deque[float]] = {}
        self._locked_until: dict[str, float] = {}
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        now = monotonic()
        with self._lock:
            locked_until = self._locked_until.get(key, 0)
            if locked_until > now:
                return False
            if locked_until:
                self._locked_until.pop(key, None)
                self._attempts.pop(key, None)
            return True

    def _purge(self, now: float) -> None:
        """Oublie les clés dont la fenêtre ou le blocage est écoulé (sinon un identifiant unique par
        tentative fait grossir la mémoire sans limite)."""
        for key in [k for k, q in self._attempts.items() if not q or q[-1] <= now - self.window_seconds]:
            self._attempts.pop(key, None)
        for key in [k for k, until in self._locked_until.items() if until <= now]:
            self._locked_until.pop(key, None)

    def record_failure(self, key: str) -> None:
        now = monotonic()
        with self._lock:
            self._purge(now)
            attempts = self._attempts.setdefault(key, deque())
            while attempts and attempts[0] <= now - self.window_seconds:
                attempts.popleft()
            attempts.append(now)
            if len(attempts) >= self.max_attempts:
                self._locked_until[key] = now + self.lockout_seconds
                attempts.clear()

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
            self._locked_until.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()
            self._locked_until.clear()
