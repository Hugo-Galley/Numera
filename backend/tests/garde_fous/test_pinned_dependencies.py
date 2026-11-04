"""Aucun tag flottant : actions GitHub épinglées par SHA de commit, images Docker par digest.

Un tag (`@v4`, `:3.12-slim`) peut être déplacé par son éditeur ; un SHA / digest ne bouge pas.
Le tag reste en commentaire (actions) ou devant le digest (images) pour la lisibilité.
"""
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]

ACTION_USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)", re.MULTILINE)
PINNED_ACTION = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
DOCKER_FROM = re.compile(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)", re.MULTILINE | re.IGNORECASE)
COMPOSE_IMAGE = re.compile(r"^\s*image:\s*['\"]?([^'\"\s#]+)", re.MULTILINE)
PINNED_IMAGE = re.compile(r"@sha256:[0-9a-f]{64}$")
# Images publiées par la release (infra/docker-compose.images.yml) : le digest n'existe pas avant le tag,
# la version est choisie par l'utilisateur via NUMERA_VERSION.
OWN_RELEASE_IMAGE = re.compile(r"^ghcr\.io/hugo-galley/numera-[a-z]+:\$\{NUMERA_VERSION(:-latest)?\}$")


def _tracked(*patterns: str) -> list[Path]:
    out = subprocess.run(["git", "ls-files", *patterns], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return [REPO_ROOT / line for line in out.stdout.splitlines()]


def floating_actions(text: str) -> list[str]:
    return [ref for ref in ACTION_USES.findall(text) if not ref.startswith("./") and not PINNED_ACTION.match(ref)]


def floating_images(text: str, stage_names: set[str] = frozenset()) -> list[str]:
    images = DOCKER_FROM.findall(text) + COMPOSE_IMAGE.findall(text)
    return [img for img in images if img not in stage_names and img != "scratch" and not PINNED_IMAGE.search(img)
            and not OWN_RELEASE_IMAGE.match(img)]


def _stage_names(text: str) -> set[str]:
    return set(re.findall(r"^\s*FROM\s+\S+\s+as\s+(\S+)", text, re.MULTILINE | re.IGNORECASE))


def test_detects_floating_action_and_image():
    assert floating_actions("      - uses: actions/checkout@v4") == ["actions/checkout@v4"]
    assert floating_actions(f"      - uses: actions/checkout@{'a' * 40} # v4.4.0") == []
    assert floating_images("FROM python:3.12-slim") == ["python:3.12-slim"]
    assert floating_images(f"FROM python:3.12-slim@sha256:{'b' * 64}") == []
    assert floating_images("FROM build-stage", {"build-stage"}) == []
    assert floating_images("    image: ghcr.io/hugo-galley/numera-backend:${NUMERA_VERSION:-latest}") == []
    assert floating_images("    image: ghcr.io/autre/numera-backend:${NUMERA_VERSION:-latest}") != []


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


TOOL_IMAGE_ENV = re.compile(r"^\s*[A-Z_]+_IMAGE:\s*(\S+)", re.MULTILINE)


def test_tool_images_in_workflows_are_pinned_by_digest():
    """Trivy, hadolint… sont lancés en conteneur depuis une variable `*_IMAGE` : même règle que les Dockerfile."""
    files = _tracked(".github/workflows/*.yml", ".github/workflows/*.yaml")
    floating = {str(f.relative_to(REPO_ROOT)): imgs for f in files
                if (imgs := [i for i in TOOL_IMAGE_ENV.findall(f.read_text()) if not PINNED_IMAGE.search(i)])}
    assert floating == {}


PRE_COMMIT_REV = re.compile(r"^\s*rev:\s*(\S+)", re.MULTILINE)


def test_pre_commit_repos_are_pinned_by_sha():
    """Les dépôts de hooks pre-commit suivent la même règle que les actions : SHA de commit, tag en commentaire."""
    text = (REPO_ROOT / ".pre-commit-config.yaml").read_text()
    floating = [rev for rev in PRE_COMMIT_REV.findall(text) if not re.fullmatch(r"[0-9a-f]{40}", rev)]
    assert floating == []


SH_IMAGE_VAR = re.compile(r"^\s*[A-Z_]*IMAGE=[\"']?([^\"'\s]+)", re.MULTILINE)


def floating_shell_images(text: str) -> list[str]:
    """Images lancées par un script shell : `docker run <image>` ou variable `*_IMAGE=` (Audit M6)."""
    images = [i for i in SH_IMAGE_VAR.findall(text) if not PINNED_IMAGE.search(i)]
    for line in text.splitlines():
        if line.lstrip().startswith("#") or "docker run" not in line:
            continue
        tokens = line.split("docker run", 1)[1].split()
        it = iter(tokens)
        for tok in it:
            if tok in {"-e", "-v", "-u", "-p", "--name", "--entrypoint"}:
                next(it, None)
                continue
            if tok.startswith("-"):
                continue
            tok = tok.strip("\"'")
            if tok.startswith("$"):  # variable : sa valeur est contrôlée par la règle *_IMAGE
                break
            if not PINNED_IMAGE.search(tok):
                images.append(tok)
            break
    return images


def floating_pip_installs(text: str) -> list[str]:
    """`pip install paquet` sans version exacte ni fichier de requirements (`-r`, avec hashes)."""
    bad = []
    for line in text.splitlines():
        if line.lstrip().startswith("#") or "pip install" not in line:
            continue
        args = line.split("pip install", 1)[1]
        if re.search(r"(^|\s)-r\s", args):
            continue
        pkgs = [t for t in args.split() if not t.startswith("-") and not t.startswith(("&", ">", "|", '"', "'"))]
        bad += [p for p in pkgs if "==" not in p]
    return bad


def test_detects_floating_shell_images_and_pip():
    assert floating_shell_images("docker run --rm -i python:3.12-slim sh -c x") == ["python:3.12-slim"]
    assert floating_shell_images(f"docker run --rm -i python:3.12@sha256:{'a' * 64} sh") == []
    assert floating_shell_images('docker run --rm -i -e A="$B" "$HASH_IMAGE" sh') == []
    assert floating_shell_images('HASH_IMAGE="python:3.12-slim"') == ["python:3.12-slim"]
    assert floating_pip_installs("pip install -q bcrypt") == ["bcrypt"]
    assert floating_pip_installs("pip install -q bcrypt==5.0.0") == []
    assert floating_pip_installs("pip install -q --require-hashes -r /tmp/r.txt") == []


def test_shell_scripts_pin_images_and_packages():
    floating = {}
    for f in _tracked("*.sh"):
        text = f.read_text()
        if refs := floating_shell_images(text) + floating_pip_installs(text):
            floating[str(f.relative_to(REPO_ROOT))] = refs
    assert floating == {}


def test_install_script_bcrypt_requirements_are_hash_pinned():
    text = (REPO_ROOT / "install.sh").read_text()
    block = re.search(r"BCRYPT_REQUIREMENTS='([^']+)'", text).group(1)
    assert re.match(r"bcrypt==\d+\.\d+\.\d+", block)
    assert len(re.findall(r"--hash=sha256:[0-9a-f]{64}", block)) >= 2
