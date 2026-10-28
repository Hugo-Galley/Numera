import asyncio
import json

from starlette.requests import Request

from app.core.errors import BusinessRuleError, ConflictError, NotFoundError
from app.main import domain_error_handler


def _handle(exc):
    response = asyncio.run(domain_error_handler(Request({"type": "http"}), exc))
    return response.status_code, json.loads(response.body)


def test_not_found_keeps_plain_detail():
    assert _handle(NotFoundError("Account not found")) == (404, {"detail": "Account not found"})


def test_business_rule_with_code_matches_api_error_shape():
    status, body = _handle(BusinessRuleError("x", code="invalid_type", context={"a": 1}))
    assert status == 422
    assert body == {"detail": {"code": "invalid_type", "detail": "x", "context": {"a": 1}}}


def test_code_without_context_gives_empty_context():
    assert _handle(BusinessRuleError("x", code="c"))[1] == {"detail": {"code": "c", "detail": "x", "context": {}}}


def test_conflict_status():
    assert _handle(ConflictError("dup"))[0] == 409


def test_domain_error_reaches_client_through_route(client):
    from fastapi import APIRouter
    from app.main import app

    router = APIRouter()

    @router.get("/__test_domain_error")
    def _raise():
        raise NotFoundError("Thing not found")

    app.include_router(router)
    try:
        response = client.get("/__test_domain_error")
    finally:
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != "/__test_domain_error"]
    assert response.status_code == 404
    assert response.json() == {"detail": "Thing not found"}


def test_internal_error_keeps_json_detail():
    from app.core.errors import InternalError

    assert _handle(InternalError("Erreur interne lors du calcul du budget")) == (
        500, {"detail": "Erreur interne lors du calcul du budget"})


def test_invalid_operation_is_400():
    from app.core.errors import InvalidOperationError

    assert _handle(InvalidOperationError("Tag name already exists")) == (400, {"detail": "Tag name already exists"})


def test_external_service_is_502():
    from app.core.errors import ExternalServiceError

    assert _handle(ExternalServiceError("Yahoo Finance est injoignable"))[0] == 502


def test_external_timeout_is_504():
    from app.core.errors import ExternalTimeoutError

    assert _handle(ExternalTimeoutError("délai dépassé"))[0] == 504
