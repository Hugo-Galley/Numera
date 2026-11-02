"""Contrat API : le schéma OpenAPI committé doit être celui que le backend expose.

Le frontend génère ses types depuis ce fichier (`npm run api:types`) : une route ou un schéma Pydantic
modifié sans régénération fait échouer ce test, au lieu de laisser le frontend diverger en silence.
Régénération : `make api-contract`.
"""
import json
import os

from app.main import app
from scripts.export_openapi import SCHEMA_PATH, render_schema


def test_committed_openapi_schema_is_up_to_date():
    expected = render_schema(app.openapi())
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        SCHEMA_PATH.write_text(expected, encoding="utf-8")
    assert json.loads(SCHEMA_PATH.read_text(encoding="utf-8")) == json.loads(expected), (
        "openapi.json périmé : lancer `make api-contract` et commiter le résultat"
    )
