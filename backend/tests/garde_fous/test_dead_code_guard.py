"""Garde-fou de code mort (vulture) : fonctions, classes, méthodes, propriétés et imports inutilisés dans `app/`.

Les tests comptent comme usage ; les variables et attributs sont ignorés (trop de faux positifs : colonnes ORM,
champs Pydantic). Un faux positif légitime se déclare dans `scripts/quality/baselines/dead_code_allowlist.json` avec son motif.
"""
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]

_spec = importlib.util.spec_from_file_location("check_dead_code", REPO_ROOT / "scripts/quality/check_dead_code.py")
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

SAMPLE = """\
app/a.py:3: unused function 'helper' (60% confidence)
app/a.py:9: unused import 'os' (90% confidence)
app/models/t.py:59: unused property 'has_claims' (60% confidence)
app/a.py:20: unused variable 'cls' (100% confidence)
app/a.py:21: unused attribute 'closed_at' (60% confidence)
tests/x.py:1: unused function 'fixture_inutile' (60% confidence)
"""


def test_parse_keeps_only_code_kinds_in_app():
    assert guard.parse(SAMPLE) == {
        "app/a.py::function helper",
        "app/a.py::import os",
        "app/models/t.py::property has_claims",
    }


def test_new_finding_fails():
    assert guard.check({"app/a.py::function helper"}, {})


def test_allowlisted_finding_passes():
    assert guard.check({"app/a.py::function helper"}, {"app/a.py::function helper": "pydantic from_attributes"}) == []


def test_stale_allowlist_entry_must_be_removed():
    assert guard.check(set(), {"app/a.py::function helper": "motif"})


def test_every_allowlist_entry_has_a_reason():
    allowlist = json.loads((REPO_ROOT / "scripts/quality/baselines/dead_code_allowlist.json").read_text())
    assert all(reason.strip() for reason in allowlist.values())


def test_repository_has_no_dead_code():
    allowlist = json.loads((REPO_ROOT / "scripts/quality/baselines/dead_code_allowlist.json").read_text())
    assert guard.check(guard.run_vulture(), allowlist) == []
