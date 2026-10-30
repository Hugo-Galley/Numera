"""Aucun tag flottant : actions GitHub épinglées par SHA de commit, images Docker par digest.

Un tag (`@v4`, `:3.12-slim`) peut être déplacé par son éditeur ; un SHA / digest ne bouge pas.
Le tag reste en commentaire (actions) ou devant le digest (images) pour la lisibilité.
"""
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]

ACTION_USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)", re.MULTILINE)
PINNED_ACTION = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
DOCKER_FROM = re.compile(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)", re.MULTILINE | re.IGNORECASE)
COMPOSE_IMAGE = re.compile(r"^\s*image:\s*['\"]?([^'\"\s#]+)", re.MULTILINE)
PINNED_IMAGE = re.compile(r"@sha256:[0-9a-f]{64}$")


def _tracked(*patterns: str) -> list[Path]:
    out = subprocess.run(["git", "ls-files", *patterns], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return [REPO_ROOT / line for line in out.stdout.splitlines()]


def floating_actions(text: str) -> list[str]:
    return [ref for ref in ACTION_USES.findall(text) if not ref.startswith("./") and not PINNED_ACTION.match(ref)]


def floating_images(text: str, stage_names: set[str] = frozenset()) -> list[str]:
    images = DOCKER_FROM.findall(text) + COMPOSE_IMAGE.findall(text)
    return [img for img in images if img not in stage_names and img != "scratch" and not PINNED_IMAGE.search(img)]


def _stage_names(text: str) -> set[str]:
    return set(re.findall(r"^\s*FROM\s+\S+\s+as\s+(\S+)", text, re.MULTILINE | re.IGNORECASE))


def test_detects_floating_action_and_image():
    assert floating_actions("      - uses: actions/checkout@v4") == ["actions/checkout@v4"]
    assert floating_actions(f"      - uses: actions/checkout@{'a' * 40} # v4.4.0") == []
    assert floating_images("FROM python:3.12-slim") == ["python:3.12-slim"]
    assert floating_images(f"FROM python:3.12-slim@sha256:{'b' * 64}") == []
    assert floating_images("FROM build-stage", {"build-stage"}) == []


def test_github_actions_are_pinned_by_sha():
    files = _tracked(".github/workflows/*.yml", ".github/workflows/*.yaml", ".github/actions/**")
    floating = {str(f.relative_to(REPO_ROOT)): refs for f in files if (refs := floating_actions(f.read_text()))}
    assert floating == {}


def test_docker_images_are_pinned_by_digest():
    files = [f for f in _tracked("*Dockerfile*", "*docker-compose*.yml", "*docker-compose*.yaml") if f.is_file()]
    floating = {}
    for f in files:
        text = f.read_text()
        if refs := floating_images(text, _stage_names(text)):
            floating[str(f.relative_to(REPO_ROOT))] = refs
    assert floating == {}
