from collections import deque
from threading import Lock
from time import monotonic

from fastapi import Request

from app.core.config import settings


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


def client_key(request: Request, username: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{username.casefold()}"


login_rate_limiter = LoginRateLimiter(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS,
    window_seconds=settings.LOGIN_WINDOW_SECONDS,
    lockout_seconds=settings.LOGIN_LOCKOUT_SECONDS,
)

# Compteur distinct du mot de passe : deviner le code après un mot de passe valide reste borné
totp_rate_limiter = LoginRateLimiter(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS,
    window_seconds=settings.LOGIN_WINDOW_SECONDS,
    lockout_seconds=settings.LOGIN_LOCKOUT_SECONDS,
)
