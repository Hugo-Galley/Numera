#!/usr/bin/env python3
"""Protège les cliquets : une PR ne peut ni relever une baseline ni baisser un seuil de couverture.

Compare les fichiers du commit courant à ceux de la branche de base (`git show BASE:chemin`) :
- baselines JSON (mypy, tailles, ESLint, code mort) : une clé nouvelle ou un compteur en hausse échoue ;
- baseline texte des couches (une violation par ligne) : une ligne nouvelle échoue ;
- seuils de couverture (`fail_under` backend, `thresholds` Vitest) : une valeur en baisse échoue.
Réduire une baseline ou relever un seuil est toujours accepté.

    python3 scripts/quality/check_ratchets.py --base origin/main
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

JSON_BASELINES = (
    "scripts/quality/baselines/mypy_baseline.json",
    "scripts/quality/baselines/code_size_baseline.json",
    "scripts/quality/baselines/dead_code_allowlist.json",
    "frontend/eslint-baseline.json",
)
LINES_BASELINES = (
    "backend/tests/garde_fous/architecture_baseline.txt",
    "backend/tests/garde_fous/architecture_rules_baseline.txt",
    "backend/tests/garde_fous/response_model_baseline.txt",
    "backend/tests/garde_fous/clock_baseline.txt",
)
COVERAGE_FILES = ("backend/.coveragerc", "frontend/vitest.config.ts")

FAIL_UNDER = re.compile(r"^\s*fail_under\s*=\s*([\d.]+)", re.MULTILINE)
VITEST_THRESHOLD = re.compile(r"\b(statements|lines|branches|functions)\s*:\s*([\d.]+)")
VITEST_BLOCK = re.compile(r"thresholds\s*:\s*\{([^}]*)\}")


def json_regressions(path: str, old, new) -> list[str]:
    """Clés ajoutées ou compteurs augmentés dans `new` par rapport à `old` (récursif)."""
    problems: list[str] = []
    if isinstance(new, dict):
        old = old if isinstance(old, dict) else {}
        for key, value in new.items():
            if key not in old:
                problems.append(f"{path}: nouvelle entrée « {key} »")
            else:
                problems += json_regressions(f"{path}::{key}", old[key], value)
    elif isinstance(new, (int, float)) and isinstance(old, (int, float)) and new > old:
        problems.append(f"{path}: {old} -> {new}")
    return problems


def line_regressions(path: str, old: str, new: str) -> list[str]:
    before = {line.strip() for line in old.splitlines() if line.strip()}
    return [f"{path}: nouvelle violation tolérée « {line.strip()} »"
            for line in new.splitlines() if line.strip() and line.strip() not in before]


def thresholds(path: str, text: str) -> dict[str, float]:
    if path.endswith(".coveragerc"):
        m = FAIL_UNDER.search(text)
        return {"fail_under": float(m[1])} if m else {}
    block = VITEST_BLOCK.search(text)
    return {k: float(v) for k, v in VITEST_THRESHOLD.findall(block[1])} if block else {}


def threshold_regressions(path: str, old: str, new: str) -> list[str]:
    before, after = thresholds(path, old), thresholds(path, new)
    problems = [f"{path}: seuil « {k} » baissé {v:g} -> {after[k]:g}" for k, v in before.items() if k in after and after[k] < v]
    problems += [f"{path}: seuil « {k} » supprimé" for k in before if k not in after]
    return problems


def base_content(base: str, path: str) -> str | None:
    result = subprocess.run(["git", "show", f"{base}:{path}"], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    return result.stdout if result.returncode == 0 else None  # absent de la base : rien à comparer


def check(base: str) -> list[str]:
    problems: list[str] = []
    for path in (*JSON_BASELINES, *LINES_BASELINES, *COVERAGE_FILES):
        old = base_content(base, path)
        file = REPO_ROOT / path
        if old is None or not file.exists():
            continue
        new = file.read_text()
        if path in JSON_BASELINES:
            problems += json_regressions(path, json.loads(old or "{}"), json.loads(new or "{}"))
        elif path in LINES_BASELINES:
            problems += line_regressions(path, old, new)
        else:
            problems += threshold_regressions(path, old, new)
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", required=True, help="référence git de la branche de base (ex. origin/main)")
    problems = check(parser.parse_args().base)
    if problems:
        print("Cliquets relâchés (baseline relevée ou seuil baissé) :")
        print("\n".join(f"  - {p}" for p in problems))
        print("Corriger le code plutôt que la baseline ; ne jamais relever un cliquet (CLAUDE.md).")
        return 1
    print("Cliquets respectés.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
