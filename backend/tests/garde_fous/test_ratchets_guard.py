"""Garde-fou des cliquets (scripts/quality/check_ratchets.py) : relâcher est refusé, resserrer est accepté."""
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]

_spec = importlib.util.spec_from_file_location("check_ratchets", REPO_ROOT / "scripts/quality/check_ratchets.py")
cr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cr)


def test_new_key_and_higher_counter_fail():
    assert cr.json_regressions("b", {"a.py": 2}, {"a.py": 3})
    assert cr.json_regressions("b", {"a.py": 2}, {"a.py": 2, "b.py": 1})


def test_lowered_or_removed_baseline_passes():
    assert cr.json_regressions("b", {"a.py": 2, "b.py": 1}, {"a.py": 1}) == []


def test_nested_counters_are_compared():
    assert cr.json_regressions("b", {"a": {"x": 1}}, {"a": {"x": 2}})


def test_new_architecture_violation_fails():
    assert cr.line_regressions("arch", "a\n", "a\nb\n") == ["arch: nouvelle violation tolérée « b »"]
    assert cr.line_regressions("arch", "a\nb\n", "a\n") == []


def test_coverage_threshold_drop_fails_raise_passes():
    old, lower, higher = "fail_under = 93\n", "fail_under = 90\n", "fail_under = 95\n"
    assert cr.threshold_regressions("backend/.coveragerc", old, lower)
    assert cr.threshold_regressions("backend/.coveragerc", old, higher) == []


def test_vitest_thresholds():
    old = "thresholds: { statements: 45, lines: 45, branches: 34, functions: 37 },"
    assert cr.threshold_regressions("vitest.config.ts", old, old.replace("branches: 34", "branches: 30"))
    assert cr.threshold_regressions("vitest.config.ts", old, old.replace("lines: 45", "lines: 50")) == []
    assert cr.threshold_regressions("vitest.config.ts", old, "") != []


def test_current_tree_has_parsable_thresholds():
    assert "fail_under" in cr.thresholds("backend/.coveragerc", (REPO_ROOT / "backend/.coveragerc").read_text())
    assert len(cr.thresholds("vitest.config.ts", (REPO_ROOT / "frontend/vitest.config.ts").read_text())) == 4


def test_head_respects_ratchets_against_itself():
    assert cr.check("HEAD") == []
