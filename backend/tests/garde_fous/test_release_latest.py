"""`:latest` et « Latest release » : seulement pour la plus haute version (correctif d'une ancienne ligne exclu)."""
import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]

_spec = importlib.util.spec_from_file_location("is_latest", REPO_ROOT / "scripts/release/is_latest.py")
il = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(il)


def test_highest_tag_is_latest():
    assert il.is_latest("v0.3.0", ["v0.1.0", "v0.2.0", "v0.2.1", "v0.3.0"])


def test_backport_on_older_line_is_not_latest():
    assert not il.is_latest("v0.2.1", ["v0.2.0", "v0.2.1", "v0.3.0"])


def test_comparison_is_numeric_not_lexical():
    assert not il.is_latest("v0.9.0", ["v0.9.0", "v0.10.0"])
    assert il.is_latest("v0.10.0", ["v0.9.0", "v0.10.0"])


def test_first_release_is_latest():
    assert il.is_latest("v0.1.0", [])


def test_non_release_tags_are_ignored():
    assert il.is_latest("v0.2.0", ["v0.2.0", "v9.9.9-rc1", "nightly"])


def test_release_workflow_gates_latest_on_the_script():
    wf = (REPO_ROOT / ".github/workflows/release.yml").read_text()
    assert "scripts/release/is_latest.py" in wf
    assert re.search(r'--latest="?\$', wf)
    # `latest` ne doit plus être codé en dur dans la liste des tags
    assert 'echo "$repo:latest"' not in wf
