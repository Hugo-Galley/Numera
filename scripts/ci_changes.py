#!/usr/bin/env python3
"""Décide, d'après les fichiers modifiés d'une PR, quelles images scanner (Trivy) et s'il faut relancer hadolint.

Un scan d'image ne change de résultat que si l'image de base, les paquets ou les dépendances déclarées changent ;
le code applicatif, les tests et la doc n'y entrent pas. Hors PR (push sur main, release), la CI scanne tout.

    git diff --name-only BASE HEAD | python3 scripts/ci_changes.py   # écrit images=… et dockerfiles=… sur stdout
"""
import sys

# Fichiers qui relancent tout : la définition des scans elle-même
EVERYTHING = (".github/workflows/ci.yml", ".trivyignore.yaml")

IMAGES = {
    "numera-backend": ("backend/Dockerfile", "backend/.dockerignore", "backend/pyproject.toml", "backend/uv.lock"),
    "numera-frontend": ("frontend/Dockerfile.prod", "frontend/.dockerignore", "frontend/package.json",
                        "frontend/package-lock.json", "frontend/nginx.conf"),
    "numera-mcp": ("mcp-server/Dockerfile", "mcp-server/.dockerignore", "mcp-server/pyproject.toml", "mcp-server/uv.lock"),
}

DOCKERFILES = ("backend/Dockerfile", "frontend/Dockerfile", "frontend/Dockerfile.prod", "mcp-server/Dockerfile",
               ".hadolint.yaml")


def classify(files: list[str]) -> dict:
    changed = set(files)
    everything = bool(changed & set(EVERYTHING))
    images = [name for name, paths in IMAGES.items() if everything or changed & set(paths)]
    return {"images": images, "dockerfiles": everything or bool(changed & set(DOCKERFILES))}


def all_watched_paths() -> set[str]:
    return {*EVERYTHING, *DOCKERFILES, *(p for paths in IMAGES.values() for p in paths)}


def main() -> None:
    result = classify([line.strip() for line in sys.stdin if line.strip()])
    print(f"images={' '.join(result['images'])}")
    print(f"dockerfiles={'true' if result['dockerfiles'] else 'false'}")


if __name__ == "__main__":
    main()
