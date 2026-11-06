#!/usr/bin/env python3
"""Dit si un tag `vX.Y.Z` est la plus haute version publiée (celle qui porte `:latest` et « Latest release »).

Un correctif posé sur `release/0.2` (tag v0.2.1) alors que v0.3.0 existe ne doit ni écraser `:latest`
ni être marquée « Latest » sur GitHub.

    python3 scripts/release/is_latest.py v0.2.1          # lit les tags du dépôt local ; affiche true ou false
"""
import re
import subprocess
import sys

TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def _key(tag: str) -> tuple[int, int, int]:
    m = TAG_RE.match(tag)
    if not m:
        raise ValueError(f"tag invalide : {tag}")
    return int(m[1]), int(m[2]), int(m[3])


def is_latest(tag: str, existing: list[str]) -> bool:
    """Vrai si aucun tag `vX.Y.Z` existant n'est strictement plus haut que `tag`."""
    mine = _key(tag)
    return all(_key(t) <= mine for t in existing if TAG_RE.match(t))


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    tags = subprocess.run(["git", "tag", "-l", "v*"], capture_output=True, text=True, check=True).stdout.split()
    print("true" if is_latest(sys.argv[1], tags) else "false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
