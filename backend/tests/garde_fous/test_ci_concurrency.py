"""La CI de `main` et des branches `release/**` est le filet qui remplace l'obligation « branche à jour » (rulesets non stricts).

Un push qui annulerait la CI du commit précédent laisserait un commit de `main` jamais testé : seules les PR
peuvent être annulées par un push plus récent, et hors PR chaque commit a son propre groupe (SHA) pour qu'une
rafale de merges ne fasse pas écraser un run en attente par le suivant.
"""
from pathlib import Path

import yaml

CI = Path(__file__).parents[3] / ".github/workflows/ci.yml"


def _concurrency() -> dict:
    return yaml.safe_load(CI.read_text(encoding="utf-8"))["concurrency"]


def test_only_pull_requests_are_cancelled():
    assert _concurrency()["cancel-in-progress"] == "${{ github.event_name == 'pull_request' }}"


def test_pushes_outside_pull_requests_get_their_own_group_per_commit():
    group = _concurrency()["group"]
    assert "github.sha" in group and "github.event_name == 'pull_request'" in group
