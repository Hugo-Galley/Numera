"""Exporte le schéma OpenAPI de l'API vers `frontend/src/lib/api/generated/openapi.json`.

Source des types TypeScript du frontend (`npm run api:types`). Lancé par `make api-contract`.
"""
import json
import os
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "api" / "generated" / "openapi.json"


def render_schema(schema: dict) -> str:
    return json.dumps(schema, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> None:
    from app.main import app

    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(render_schema(app.openapi()), encoding="utf-8")
    print(f"écrit : {SCHEMA_PATH}")


if __name__ == "__main__":
    main()
