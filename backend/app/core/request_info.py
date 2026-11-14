"""Ce que le backend lit d'une requête HTTP (sans dépendre de FastAPI) : en-têtes et adresse du client."""
from collections.abc import Mapping
from typing import Protocol


class _Address(Protocol):
    @property
    def host(self) -> str: ...


class RequestInfo(Protocol):
    """`fastapi.Request` y répond tel quel ; les services et le noyau ne connaissent que ce contrat."""

    @property
    def headers(self) -> Mapping[str, str]: ...

    @property
    def client(self) -> _Address | None: ...


def client_ip(request: RequestInfo) -> str | None:
    """Adresse du client : en production, Nginx la transmet dans X-Real-IP (le backend n'est pas exposé)."""
    forwarded = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "").split(",")[0]
    if forwarded.strip():
        return forwarded.strip()[:64]
    return request.client.host if request.client else None
