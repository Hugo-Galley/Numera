"""Une seule version de Python et de Node : poste, CI et images Docker doivent s'accorder.

`.python-version` et `.nvmrc` sont la référence (lus par uv, pyenv, nvm, fnm) ; Python 3.14 est exclu
(pydantic-core incompatible), cf. `requires-python` de `backend/pyproject.toml`.
"""
import re
from pathlib import Path

ROOT = Path(__file__).parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_python_version_is_consistent():
    version = _read(".python-version").strip()
    assert re.fullmatch(r"3\.1[12]", version)
    assert re.findall(r"^FROM python:([\d.]+)-slim", _read("backend/Dockerfile"), re.MULTILINE) == [version, version]
    assert set(re.findall(r'python-version: "([\d.]+)"', _read(".github/workflows/ci.yml"))) == {version}
    assert re.search(r'requires-python = ">=3\.11,<3\.13"', _read("backend/pyproject.toml"))


def test_node_version_is_consistent():
    major = _read(".nvmrc").strip()
    assert re.fullmatch(r"\d+", major)
    assert re.findall(r"^FROM node:(\d+)-alpine", _read("frontend/Dockerfile.prod"), re.MULTILINE) == [major]
    assert set(re.findall(r'node-version: "(\d+)"', _read(".github/workflows/ci.yml"))) == {major}
    assert f">={major}" in _read("frontend/package.json")
