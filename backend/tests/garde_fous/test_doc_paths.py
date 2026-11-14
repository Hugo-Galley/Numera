"""Un chemin de fichier cité entre accents graves dans la documentation doit exister dans le dépôt.

Un fichier déplacé laisse une doc fausse (`components/layout/Omnibox.tsx`, `core/login_events.py`…) que rien
ne signalait. La doc cite souvent un chemin partiel (`portfolio/cache.py`) : il suffit qu'un fichier suivi par
git se termine par ce chemin, à une frontière de dossier.
"""
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]

DOC_FILES = ("*.md", ".claude/skills/*/SKILL.md")
# Licence d'un jeu d'icônes tiers : pas notre documentation
SKIPPED_DOCS = {"backend/app/assets/simple_icons/LICENSE.md"}

EXTENSIONS = "py|ts|tsx|js|mjs|cjs|json|md|yml|yaml|sh|toml|ini|css|conf|txt|html|cfg"
# `dossier/fichier.ext`, éventuellement suivi de `::symbole` ou `:ligne` ; au moins un `/` (un nom nu est ambigu)
CITED_PATH = re.compile(rf"`([\w.@\-]+(?:/[\w.@\-]+)+\.(?:{EXTENSIONS}))(?:::?[\w.]+)?`")

# Fichiers cités à raison mais absents du dépôt (produits à l'exécution, locaux) : préfixes à compléter au besoin
NOT_IN_REPO: tuple[str, ...] = (
    "dist/",  # produit par `vite build`
    "BACKUP_DIR/",  # dossier de sauvegarde, `status.json` écrit par scripts/backup.py
)


def cited_paths(text: str) -> list[str]:
    """Chemins de fichiers cités entre accents graves, dans l'ordre, sans doublon."""
    return list(dict.fromkeys(CITED_PATH.findall(text)))


def is_known(path: str, tracked: set[str]) -> bool:
    """Vrai si un fichier suivi est ce chemin ou se termine par lui à une frontière de dossier."""
    path = path.removeprefix("./")
    return path in tracked or any(name.endswith("/" + path) for name in tracked)


def missing_paths(text: str, tracked: set[str]) -> list[str]:
    return [
        path
        for path in cited_paths(text)
        if not is_known(path, tracked) and not path.startswith(NOT_IN_REPO)
    ]


def _git_files(*patterns: str) -> list[str]:
    out = subprocess.run(["git", "ls-files", *patterns], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return out.stdout.splitlines()


def test_cited_paths_keeps_only_backticked_files_with_a_folder():
    text = "Voir `services/budget/balances.py::recalculate`, `lib/api.ts:42`, `make test`, `utils.py` et lib/x.ts."

    assert cited_paths(text) == ["services/budget/balances.py", "lib/api.ts"]


def test_partial_path_matches_only_at_a_folder_boundary():
    tracked = {"backend/app/services/investissement/portfolio/cache.py"}

    assert is_known("portfolio/cache.py", tracked)
    assert is_known("backend/app/services/investissement/portfolio/cache.py", tracked)
    assert not is_known("folio/cache.py", tracked)


def test_moved_file_is_reported():
    tracked = {"frontend/src/components/layout/Omnibox/index.tsx"}

    assert missing_paths("Omnibox (`components/layout/Omnibox.tsx`)", tracked) == ["components/layout/Omnibox.tsx"]
    assert missing_paths("Omnibox (`components/layout/Omnibox/index.tsx`)", tracked) == []


def test_every_path_cited_in_the_docs_exists():
    tracked = set(_git_files())
    problems = []
    for doc in _git_files(*DOC_FILES):
        if doc in SKIPPED_DOCS:
            continue
        text = (REPO_ROOT / doc).read_text(encoding="utf-8")
        problems.extend(f"{doc} : `{path}`" for path in missing_paths(text, tracked))

    assert not problems, (
        "Chemins cités dans la doc mais absents du dépôt (fichier déplacé ou renommé ?). Corriger la doc, ou "
        "ajouter le chemin à NOT_IN_REPO s'il est produit à l'exécution :\n" + "\n".join(problems)
    )
