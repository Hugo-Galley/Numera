"""Classement des fichiers modifiés d'une PR : quelles images scanner (Trivy), faut-il relancer hadolint.

Un scan d'image ne change de résultat que si l'image de base, les paquets ou les dépendances déclarées changent :
une PR qui ne touche que du code applicatif, des tests ou de la doc ne relance pas les scans (le scan hebdomadaire
`security.yml` et la CI de `main` scannent tout de toute façon).
"""
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]

_spec = importlib.util.spec_from_file_location("ci_changes", REPO_ROOT / "scripts/ci/ci_changes.py")
ci_changes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ci_changes)

ALL_IMAGES = ["numera-backend", "numera-frontend", "numera-mcp"]


def test_application_code_tests_and_docs_scan_nothing():
    files = ["backend/app/services/budget/balances.py", "frontend/src/pages/Login.tsx", "docs/BACKEND.md", "README.md"]
    assert ci_changes.classify(files) == {"images": [], "dockerfiles": False}


def test_each_image_is_scanned_when_its_dependencies_change():
    assert ci_changes.classify(["backend/uv.lock"])["images"] == ["numera-backend"]
    assert ci_changes.classify(["frontend/package-lock.json"])["images"] == ["numera-frontend"]
    assert ci_changes.classify(["frontend/nginx.conf"])["images"] == ["numera-frontend"]
    assert ci_changes.classify(["mcp-server/pyproject.toml"])["images"] == ["numera-mcp"]


def test_a_dockerfile_change_scans_its_image_and_runs_hadolint():
    assert ci_changes.classify(["mcp-server/Dockerfile"]) == {"images": ["numera-mcp"], "dockerfiles": True}
    assert ci_changes.classify(["frontend/Dockerfile"]) == {"images": [], "dockerfiles": True}
    assert ci_changes.classify([".hadolint.yaml"]) == {"images": [], "dockerfiles": True}


def test_ci_workflow_or_trivy_ignore_rescans_everything():
    assert ci_changes.classify([".github/workflows/ci.yml"]) == {"images": ALL_IMAGES, "dockerfiles": True}
    assert ci_changes.classify([".trivyignore.yaml"])["images"] == ALL_IMAGES


def test_every_path_in_the_mapping_exists():
    """Un fichier renommé ou supprimé ferait sauter son scan en silence."""
    missing = [p for p in ci_changes.all_watched_paths() if not (REPO_ROOT / p).exists()]
    assert missing == []
