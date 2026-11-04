"""Le compose « images publiées » ne doit pas dériver du compose de production.

`docker-compose.images.yml` est joint à chaque Release (renommé `docker-compose.yml`) : il décrit les
mêmes services que `docker-compose.prod.yml`, mais avec les images GHCR au lieu de `build:`.
"""
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[3]
PUBLISHED = {
    "backend": "numera-backend",
    "backup": "numera-backend",
    "mcp-server": "numera-mcp",
    "frontend": "numera-frontend",
}
# Seuls ces champs diffèrent volontairement (construction locale / chemins de volumes).
DIFFERENT = {"build", "image", "volumes"}


def load(name: str) -> dict:
    return yaml.safe_load((REPO_ROOT / name).read_text())["services"]


def test_same_services_and_settings_as_prod():
    prod, images = load("infra/docker-compose.prod.yml"), load("infra/docker-compose.images.yml")
    assert set(images) == set(prod)
    for name, service in prod.items():
        wanted = {k: v for k, v in service.items() if k not in DIFFERENT}
        got = {k: v for k, v in images[name].items() if k not in DIFFERENT}
        assert got == wanted, name


def test_images_are_ours_and_never_built():
    for name, service in load("infra/docker-compose.images.yml").items():
        assert "build" not in service, name
        assert service["image"] == f"ghcr.io/hugo-galley/{PUBLISHED[name]}:${{NUMERA_VERSION:-latest}}", name


def test_data_lives_next_to_the_compose_file():
    for name, service in load("infra/docker-compose.images.yml").items():
        for volume in service.get("volumes", []):
            assert not volume.startswith("./backend/"), f"{name}: {volume}"
