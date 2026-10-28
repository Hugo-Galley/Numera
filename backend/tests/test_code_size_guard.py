import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]

_spec = importlib.util.spec_from_file_location("check_code_size", REPO_ROOT / "scripts/check_code_size.py")
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_new_oversized_file_fails(tmp_path):
    write(tmp_path / "backend/app/big.py", "x = 1\n" * 401)
    assert len(guard.check(guard.measure(tmp_path), {})) == 1


def test_file_at_limit_passes(tmp_path):
    write(tmp_path / "backend/app/ok.py", "x = 1\n" * 400)
    assert guard.measure(tmp_path) == {}


def test_baselined_file_may_not_grow():
    assert guard.check({"backend/app/big.py": 450}, {"backend/app/big.py": 420})


def test_baselined_file_that_shrinks_but_stays_over_limit_passes():
    assert guard.check({"backend/app/big.py": 410}, {"backend/app/big.py": 420}) == []


def test_baselined_file_back_under_limit_must_be_removed():
    assert guard.check({}, {"backend/app/big.py": 420})


def test_long_function_has_qualified_key(tmp_path):
    body = "class A:\n    def m(self):\n" + "        x = 1\n" * 85
    write(tmp_path / "backend/app/a.py", body)
    assert "backend/app/a.py::A.m" in guard.measure(tmp_path)


def test_frontend_file_limit(tmp_path):
    write(tmp_path / "frontend/src/pages/Big.tsx", "x\n" * 351)
    assert guard.measure(tmp_path) == {"frontend/src/pages/Big.tsx": 351}


def test_ui_components_are_ignored(tmp_path):
    write(tmp_path / "frontend/src/components/ui/table.tsx", "x\n" * 500)
    assert guard.measure(tmp_path) == {}


def test_repository_matches_baseline():
    baseline = json.loads((REPO_ROOT / "scripts/code_size_baseline.json").read_text())
    assert guard.check(guard.measure(REPO_ROOT), baseline) == []
