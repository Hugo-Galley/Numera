#!/usr/bin/env python3
"""Garde-fou de types : mypy sur backend/app, avec baseline à cliquet.

`app/domain/` et `app/core/` sont stricts (backend/mypy.ini) : aucune erreur tolérée.
Ailleurs, les erreurs existantes sont comptées par fichier dans `mypy_baseline.json` :
un fichier ne peut pas avoir plus d'erreurs que sa baseline, et une entrée doit être
retirée (ou diminuée) dès que le fichier s'améliore.

    python3 scripts/check_types.py                    # contrôle (code 1 si erreur)
    python3 scripts/check_types.py --write-baseline   # régénère la baseline (à ne faire que pour la diminuer)
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = Path(__file__).resolve().parent / "mypy_baseline.json"
STRICT_PREFIXES = ("app/domain/", "app/core/")
ERROR_RE = re.compile(r"^(app/[^:]+\.py):\d+: error:")


def run_mypy() -> tuple[Counter[str], str]:
    python = os.environ.get("PYTHON", sys.executable)
    result = subprocess.run(
        [python, "-m", "mypy"], cwd=REPO_ROOT / "backend", capture_output=True, text=True, check=False
    )
    if "No module named mypy" in result.stderr:
        sys.exit("mypy introuvable : pip install -r backend/requirements-dev.txt")
    counts: Counter[str] = Counter()
    for line in result.stdout.splitlines():
        match = ERROR_RE.match(line)
        if match:
            counts[match.group(1)] += 1
    return counts, result.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args()

    counts, output = run_mypy()
    if args.write_baseline:
        tolerated = {f: n for f, n in sorted(counts.items()) if not f.startswith(STRICT_PREFIXES)}
        BASELINE_PATH.write_text(json.dumps(tolerated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Baseline écrite : {sum(tolerated.values())} erreurs dans {len(tolerated)} fichiers.")
        return 0

    baseline: dict[str, int] = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []
    for path, count in sorted(counts.items()):
        allowed = 0 if path.startswith(STRICT_PREFIXES) else baseline.get(path, 0)
        if count > allowed:
            problems.append(f"{path} : {count} erreurs de types (autorisé : {allowed})")
    for path, allowed in sorted(baseline.items()):
        if counts.get(path, 0) < allowed:
            problems.append(
                f"{path} : baseline obsolète ({allowed} → {counts.get(path, 0)}), "
                "relancer avec --write-baseline pour la réduire"
            )
    if problems:
        print("\n".join(problems))
        print("\nDétail : cd backend && python -m mypy | grep <fichier>")
        return 1
    print(f"Types OK ({sum(counts.values())} erreurs tolérées par la baseline, 0 dans app/domain et app/core)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
