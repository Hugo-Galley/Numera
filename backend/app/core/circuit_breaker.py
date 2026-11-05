"""Disjoncteur simple pour les services externes (Yahoo, Frankfurter).

Après `threshold` échecs consécutifs, `allow()` refuse pendant `cooldown` : on cesse de réinterroger un service
en panne (chaque appel coûte jusqu'au timeout). Un succès referme le disjoncteur. État local au processus."""
from datetime import datetime, timedelta

from app.core.time import utcnow_naive

_REGISTRY: list["CircuitBreaker"] = []


class CircuitBreaker:
    def __init__(self, threshold: int = 3, cooldown: timedelta = timedelta(minutes=5)) -> None:
        self.threshold = threshold
        self.cooldown = cooldown
        self._failures = 0
        self._open_until: datetime | None = None
        _REGISTRY.append(self)

    def allow(self) -> bool:
        return self._open_until is None or utcnow_naive() >= self._open_until

    def success(self) -> None:
        self._failures = 0
        self._open_until = None

    def failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self._open_until = utcnow_naive() + self.cooldown

    def reset(self) -> None:
        self.success()


def reset_all() -> None:
    for breaker in _REGISTRY:
        breaker.reset()
