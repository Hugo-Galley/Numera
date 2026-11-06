#!/usr/bin/env python3
"""Garde-fou de code mort : vulture sur backend/app (les tests comptent comme usage).

Seuls les fonctions, classes, méthodes, propriétés et imports inutilisés sont contrôlés : les variables et
attributs produisent trop de faux positifs (colonnes ORM, champs Pydantic). Un faux positif légitime se
déclare dans `dead_code_allowlist.json` (`"fichier::nature nom": "motif"`) ; une entrée devenue inutile
doit être retirée.

    python3 scripts/quality/check_dead_code.py     # contrôle (code 1 si écart)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST_PATH = Path(__file__).resolve().parent / "baselines" / "dead_code_allowlist.json"
BACKEND = REPO_ROOT / "backend"

KINDS = ("function", "class", "method", "property", "import", "unreachable code")
LINE_RE = re.compile(r"^(app/[^:]+\.py):\d+: unused (" + "|".join(KINDS) + r") '([^']+)'")
IGNORE_DECORATORS = "@router.*,@app.*,@field_validator,@model_validator,@validates,@event.*,@lru_cache"


def parse(output: str) -> set[str]:
    found = set()
    for line in output.splitlines():
        if match := LINE_RE.match(line):
            found.add(f"{match[1]}::{match[2]} {match[3]}")
    return found


def run_vulture() -> set[str]:
    # `python -m vulture` : l'interpréteur courant (celui du venv), sans dépendre du PATH
    result = subprocess.run(
        [sys.executable, "-m", "vulture", "app", "tests", "--min-confidence", "60", "--ignore-decorators", IGNORE_DECORATORS],
        cwd=BACKEND, capture_output=True, text=True,
    )
    if result.returncode not in (0, 3):  # 3 = code mort trouvé
        raise RuntimeError(f"vulture a échoué : {result.stderr}")
    return parse(result.stdout)


def check(found: set[str], allowlist: dict[str, str]) -> list[str]:
    errors = [f"code mort : {item} (le supprimer, ou le déclarer dans dead_code_allowlist.json avec son motif)"
              for item in sorted(found - allowlist.keys())]
    errors += [f"allowlist périmée : {item} (n'est plus signalé, retirer l'entrée)" for item in sorted(allowlist.keys() - found)]
    return errors


def main() -> int:
    allowlist = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    errors = check(run_vulture(), allowlist)
    for error in errors:
        print(error)
    if not errors:
        print("Code mort : aucun")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
