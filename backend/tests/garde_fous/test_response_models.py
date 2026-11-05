"""Tout endpoint déclare son contrat de réponse : `response_model` (ou annotation de retour), ou `status_code=204`.

Sans contrat, le schéma OpenAPI et les types générés du frontend sont `unknown`. Les endpoints qui n'en ont pas
encore sont tolérés via `response_model_baseline.txt` (cliquet : aucune nouvelle entrée, une entrée corrigée
doit être retirée).

    cd backend && APP_ENV=test PYTHONPATH=. python3.11 tests/garde_fous/test_response_models.py   # régénère la baseline
"""
from pathlib import Path

from app.main import app

BASELINE_PATH = Path(__file__).parent / "response_model_baseline.txt"


def _has_contract(response: dict) -> bool:
    """Une réponse typée expose un schéma non vide ; sans `response_model`, FastAPI publie `{}`."""
    return any(media.get("schema") for media in response.get("content", {}).values())


def endpoints_without_contract(openapi: dict | None = None) -> set[str]:
    """« METHODE chemin » des opérations dont une réponse 2xx (hors 204) n'a pas de schéma.

    Lu dans le schéma OpenAPI : `app.routes` ne liste plus les routes à plat (routers inclus paresseusement).
    """
    paths = (openapi or app.openapi())["paths"]
    return {
        f"{method.upper()} {path}"
        for path, item in paths.items()
        for method, operation in item.items()
        if any(code.startswith("2") and code != "204" and not _has_contract(resp) for code, resp in operation["responses"].items())
    }


def _baseline() -> set[str]:
    return set(BASELINE_PATH.read_text(encoding="utf-8").splitlines()) - {""}


def test_detects_untyped_and_accepts_204():
    spec = {"paths": {
        "/a": {"get": {"responses": {"200": {"content": {"application/json": {"schema": {}}}}}}},
        "/b": {"get": {"responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/x"}}}}}}},
        "/c": {"delete": {"responses": {"204": {"description": "ok"}}}},
    }}
    assert endpoints_without_contract(spec) == {"GET /a"}


def test_every_endpoint_has_a_response_model():
    found, baseline = endpoints_without_contract(), _baseline()
    assert sorted(found - baseline) == [], "nouvel endpoint sans response_model (ni 204)"
    assert sorted(baseline - found) == [], f"endpoints désormais typés : les retirer de {BASELINE_PATH.name}"


if __name__ == "__main__":
    BASELINE_PATH.write_text("\n".join(sorted(endpoints_without_contract())) + "\n", encoding="utf-8")
    print(f"Baseline écrite : {BASELINE_PATH}")
