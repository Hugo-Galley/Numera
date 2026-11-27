"""Jeux de test des émetteurs d'ETF (réponses réelles du 26/11/2026, réduites) servis par `httpx.MockTransport`."""
from collections.abc import Callable
from pathlib import Path

import httpx

FIXTURES = Path(__file__).parent / "fixtures" / "etf_providers"


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def mock_factory(handler: Callable[[httpx.Request], httpx.Response], seen: list[httpx.Request] | None = None):
    """Fabrique de clients dont chaque requête est servie par `handler` ; `seen` reçoit les requêtes."""

    def wrapped(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return handler(request)

    return lambda: httpx.AsyncClient(transport=httpx.MockTransport(wrapped))
