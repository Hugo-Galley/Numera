from typing import Any


class DomainError(Exception):
    """Erreur métier levée par un service ; traduite en HTTP par `domain_error_handler` (main.py).

    Sans `code`, le corps est `{"detail": detail}` ; avec, `{"detail": {"code", "detail", "context"}}`.
    """

    status_code = 400
    headers: dict[str, str] | None = None

    def __init__(self, detail: str, code: str | None = None, context: dict[str, Any] | None = None):
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.context = context

    def to_content(self) -> dict[str, Any]:
        if self.code is None:
            return {"detail": self.detail}
        return {"detail": {"code": self.code, "detail": self.detail, "context": self.context or {}}}


class NotFoundError(DomainError):
    status_code = 404


class BusinessRuleError(DomainError):
    status_code = 422


class ConflictError(DomainError):
    status_code = 409


class InternalError(DomainError):
    """Échec inattendu d'un calcul : 500 avec un `detail` JSON (comme l'ancienne HTTPException 500)."""

    status_code = 500


class InvalidOperationError(DomainError):
    """Opération refusée par une règle métier, renvoyée en 400 (jamais 401/403 : le client déconnecte)."""

    status_code = 400


class ExternalServiceError(DomainError):
    """Service externe injoignable ou en erreur (Yahoo, ntfy, Telegram…)."""

    status_code = 502


class ExternalTimeoutError(DomainError):
    status_code = 504


class AuthenticationError(DomainError):
    """Identifiants ou jeton d'étape refusés : 401 (le client déconnecte l'utilisateur sur ce code)."""

    status_code = 401

    def __init__(self, detail: str, www_authenticate: bool = False):
        super().__init__(detail)
        if www_authenticate:
            self.headers = {"WWW-Authenticate": "Bearer"}


class RateLimitedError(DomainError):
    """Trop de tentatives : 429 avec `Retry-After`."""

    status_code = 429

    def __init__(self, detail: str, retry_after_seconds: int):
        super().__init__(detail)
        self.headers = {"Retry-After": str(retry_after_seconds)}
