"""Ensemble (méthode, chemin) des routes de l'API, figé pour les renommages de modules (phase 6).

Régénération : `UPDATE_SNAPSHOTS=1 PYTHONPATH=. python3.11 -m pytest tests/test_openapi_routes.py`.
"""
import json
import os
from pathlib import Path

from app.main import app

SNAPSHOT_PATH = Path(__file__).parents[1] / "snapshots" / "openapi_routes.json"


def _routes() -> list[str]:
    return sorted(f"{method.upper()} {path}" for path, item in app.openapi()["paths"].items() for method in item)


def test_openapi_routes_unchanged():
    routes = _routes()
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        SNAPSHOT_PATH.write_text(json.dumps(routes, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    assert routes == json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
