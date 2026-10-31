"""Notes de version et choix du bump SemVer à partir des commits Conventional Commits."""
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]

_spec = importlib.util.spec_from_file_location("release_notes", REPO_ROOT / "scripts/release_notes.py")
rn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rn)


def commit(subject: str, body: str = "") -> "rn.Commit":
    return rn.parse_commit("a" * 40, subject, body)


def test_parse_conventional_subject():
    c = commit("feat(budget): revue du mois")
    assert (c.type, c.scope, c.description, c.breaking) == ("feat", "budget", "revue du mois", False)


def test_parse_without_scope_and_breaking_marker():
    c = commit("refactor!: renomme la table")
    assert (c.type, c.scope, c.breaking) == ("refactor", None, True)


def test_breaking_change_in_body():
    assert commit("feat(api): nouvelle route", "BREAKING CHANGE: ancienne route supprimée").breaking


def test_non_conventional_subject_is_other():
    assert commit("Merge branch 'main' of github").type == "other"


def test_bump_major_on_breaking():
    assert rn.suggest_bump([commit("fix: a"), commit("feat!: b")]) == "major"


def test_bump_minor_on_feat():
    assert rn.suggest_bump([commit("fix: a"), commit("feat: b")]) == "minor"


def test_bump_patch_on_fix_only():
    assert rn.suggest_bump([commit("fix: a"), commit("docs: b")]) == "patch"


def test_bump_none_when_nothing_user_visible():
    assert rn.suggest_bump([commit("docs: a"), commit("test: b"), commit("chore: c")]) is None


def test_bump_version():
    assert rn.bump_version("0.3.2", "patch") == "0.3.3"
    assert rn.bump_version("0.3.2", "minor") == "0.4.0"
    assert rn.bump_version("0.3.2", "major") == "1.0.0"


def test_notes_group_by_type_and_hide_noise():
    notes = rn.render_notes(
        "0.2.0",
        [commit("feat(budget): revue du mois"), commit("fix(ui): menu"), commit("test: e2e"), commit("docs: readme")],
    )
    assert "## Nouveautés" in notes and "**budget** : revue du mois" in notes
    assert "## Corrections" in notes and "**ui** : menu" in notes
    assert "e2e" not in notes and "readme" not in notes


def test_notes_flag_breaking_changes_first():
    notes = rn.render_notes("1.0.0", [commit("feat: a"), commit("fix!: b")])
    assert notes.index("Changements incompatibles") < notes.index("Nouveautés")
