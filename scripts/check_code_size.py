#!/usr/bin/env python3
"""Garde-fou de taille : fichiers et fonctions au-delà des plafonds.

Les dépassements existants sont tolérés via `code_size_baseline.json` (cliquet) :
une entrée ne peut pas grossir, et doit être retirée dès qu'elle repasse sous le plafond.

    python3 scripts/check_code_size.py                    # contrôle (code 1 si erreur)
    python3 scripts/check_code_size.py --write-baseline   # régénère la baseline
"""
import argparse
import ast
import json
import sys
from pathlib import Path

LIMITS = {"py_file": 400, "py_function": 80, "ts_file": 350}

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = Path(__file__).resolve().parent / "code_size_baseline.json"

BACKEND_DIR = "backend/app"
FRONTEND_DIR = "frontend/src"
FRONTEND_IGNORED = "frontend/src/components/ui/"


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _function_lengths(tree: ast.AST, prefix: str = ""):
    """(nom qualifié, nb de lignes) pour chaque fonction, méthode et fonction imbriquée."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = f"{prefix}{node.name}"
            yield name, node.end_lineno - node.lineno + 1
            yield from _function_lengths(node, f"{name}.")
        elif isinstance(node, ast.ClassDef):
            yield from _function_lengths(node, f"{prefix}{node.name}.")
        else:
            yield from _function_lengths(node, prefix)


def _python_files(repo_root: Path):
    for path in sorted((repo_root / BACKEND_DIR).rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


def _frontend_files(repo_root: Path):
    for pattern in ("*.ts", "*.tsx"):
        for path in sorted((repo_root / FRONTEND_DIR).rglob(pattern)):
            rel = path.relative_to(repo_root).as_posix()
            if rel.startswith(FRONTEND_IGNORED) or rel.endswith(".d.ts"):
                continue
            yield path


def measure(repo_root: Path) -> dict[str, int]:
    """Mesures au-dessus du plafond, clés relatives à la racine du dépôt."""
    over: dict[str, int] = {}
    for path in _python_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        lines = _line_count(path)
        if lines > LIMITS["py_file"]:
            over[rel] = lines
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name, length in _function_lengths(tree):
            if length > LIMITS["py_function"]:
                over[f"{rel}::{name}"] = length
    for path in _frontend_files(repo_root):
        lines = _line_count(path)
        if lines > LIMITS["ts_file"]:
            over[path.relative_to(repo_root).as_posix()] = lines
    return over


def check(measures: dict[str, int], baseline: dict[str, int]) -> list[str]:
    errors: list[str] = []
    for key, size in sorted(measures.items()):
        if key not in baseline:
            errors.append(f"{key} : {size} lignes, au-delà du plafond (découper ce code)")
        elif size > baseline[key]:
            errors.append(f"{key} : {size} lignes, a grossi depuis la baseline ({baseline[key]})")
    for key in sorted(baseline.keys() - measures.keys()):
        errors.append(f"{key} : repassé sous le plafond (ou disparu), le retirer de {BASELINE_PATH.name}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write-baseline", action="store_true", help="régénère la baseline")
    args = parser.parse_args(argv)

    measures = measure(REPO_ROOT)
    if args.write_baseline:
        BASELINE_PATH.write_text(json.dumps(measures, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        print(f"{len(measures)} entrées écrites dans {BASELINE_PATH.relative_to(REPO_ROOT)}")
        return 0

    baseline = json.loads(BASELINE_PATH.read_text()) if BASELINE_PATH.exists() else {}
    errors = check(measures, baseline)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f"Tailles OK ({len(baseline)} dépassements tolérés par la baseline)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
