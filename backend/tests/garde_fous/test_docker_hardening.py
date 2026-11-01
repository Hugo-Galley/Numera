"""Durcissement des images et des conteneurs : pas de root, système de fichiers en lecture seule, sans privilèges.

Un Dockerfile ou un service compose qui perd l'une de ces protections doit faire échouer la CI.
"""
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[3]
# Images publiées ou construites pour la production (frontend/Dockerfile est l'image de développement).
PROD_DOCKERFILES = ["backend/Dockerfile", "frontend/Dockerfile.prod", "mcp-server/Dockerfile"]
COMPOSE_FILES = ["docker-compose.prod.yml", "docker-compose.images.yml", "docker-compose.demo.yml"]
NON_ROOT = re.compile(r"^(?!root$|0$)\S+$")


def final_user(dockerfile: str) -> str | None:
    """Dernier `USER` de l'étape finale (celle du dernier `FROM`)."""
    text = (REPO_ROOT / dockerfile).read_text()
    final_stage = re.split(r"(?im)^FROM\s", text)[-1]
    users = re.findall(r"(?im)^USER\s+(\S+)", final_stage)
    return users[-1] if users else None


def test_final_stage_runs_as_non_root():
    for dockerfile in PROD_DOCKERFILES:
        user = final_user(dockerfile)
        assert user and NON_ROOT.match(user), f"{dockerfile}: USER final = {user!r}"


def test_images_declare_a_healthcheck():
    for dockerfile in PROD_DOCKERFILES:
        assert re.search(r"(?m)^HEALTHCHECK\s", (REPO_ROOT / dockerfile).read_text()), dockerfile


def test_runtime_image_has_no_compiler_or_curl():
    runtime = re.split(r"(?im)^FROM\s", (REPO_ROOT / "backend/Dockerfile").read_text())[-1]
    assert not re.search(r"\b(gcc|curl|python3-dev)\b", runtime)


def test_every_compose_service_is_locked_down():
    for name in COMPOSE_FILES:
        for service, conf in yaml.safe_load((REPO_ROOT / name).read_text())["services"].items():
            where = f"{name}:{service}"
            assert conf.get("read_only") is True, where
            assert conf.get("cap_drop") == ["ALL"], where
            assert "no-new-privileges:true" in conf.get("security_opt", []), where
            assert "privileged" not in conf, where
