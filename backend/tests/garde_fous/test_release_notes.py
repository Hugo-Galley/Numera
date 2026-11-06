"""Notes de version et choix du bump SemVer à partir des commits Conventional Commits."""
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]

_spec = importlib.util.spec_from_file_location("release_notes", REPO_ROOT / "scripts/release/release_notes.py")
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
    assert "## ✨ À la une" in notes and "### Revue du mois" in notes
    assert "## 🐛 Corrections" in notes and "**Interface** · Menu" in notes
    assert "e2e" not in notes and "readme" not in notes


def test_notes_flag_breaking_changes_first():
    notes = rn.render_notes("1.0.0", [commit("feat: a"), commit("fix!: b")])
    assert notes.index("Changements incompatibles") < notes.index("À la une")


def test_pr_number_becomes_a_link_not_text():
    c = commit("fix(budget): bornes exclusives (#62)")
    assert (c.description, c.pr) == ("bornes exclusives", 62)
    notes = rn.render_notes("0.3.0", [c], repo="o/r")
    assert "([#62](https://github.com/o/r/pull/62))" in notes and "(#62)" not in notes.replace("[#62]", "")


def test_highlights_use_body_summary_without_trailers_and_prefer_documented_feats():
    body = "Pourquoi : le solde bougeait trop tôt.\nSuite de la phrase.\n\n- détail technique\n\nCo-Authored-By: X <x@y>"
    notes = rn.render_notes(
        "0.3.0", [commit("feat(a): sans corps"), commit("feat(b): avec corps", body)] + [commit(f"feat(c): n{i}") for i in range(3)]
    )
    highlights = notes.split("## ✨ À la une")[1].split("\n## ")[0]
    assert "Pourquoi : le solde bougeait trop tôt. Suite de la phrase." in highlights
    assert "détail technique" not in highlights and "Co-Authored" not in notes
    assert highlights.count("### ") == rn.HIGHLIGHTS_MAX
    assert highlights.index("Avec corps") < highlights.index("Sans corps")


def test_highlighted_feats_are_not_repeated_in_the_list():
    notes = rn.render_notes("0.3.0", [commit("feat(a): un"), commit("feat(a): deux"), commit("feat(a): trois"), commit("feat(a): quatre")])
    assert "## 🆕 Nouveautés" in notes
    rest = notes.split("## 🆕 Nouveautés")[1]
    assert "Quatre" in rest and "Un" not in rest.split("## Mettre")[0].replace("Quatre", "")


def test_tooling_scopes_and_refactors_go_under_the_hood():
    notes = rn.render_notes("0.3.0", [commit("feat(qualité): mypy"), commit("refactor(budget): découpage"), commit("fix(x): y")])
    hood = notes.split("## 🔧 Sous le capot")[1]
    assert "Mypy" in hood and "Découpage" in hood
    assert "À la une" not in notes


def test_summary_is_cut_on_a_word_boundary():
    text = rn.summary(commit("feat: x", "mot " * 200))
    assert text.endswith("…") and len(text) <= rn.SUMMARY_MAX + 1 and "mo…" not in text


def test_notes_end_with_update_help_and_compare_link():
    notes = rn.render_notes("0.3.0", [commit("fix: a")], repo="o/r", previous="v0.2.0")
    assert "docker compose pull" in notes
    assert "https://github.com/o/r/compare/v0.2.0...v0.3.0" in notes
    assert "compare" not in rn.render_notes("0.3.0", [commit("fix: a")])
