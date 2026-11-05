"""L'horloge passe par `app/core/time.py` : ni `datetime.now(`, ni `date.today(`, ni `utcnow(` ailleurs.

Un appel direct empêche de figer le temps dans les tests et mélange heure locale et UTC naïf (convention
de la base). `datetime.utcnow()` est de plus déprécié : utiliser `core.time.utcnow_naive`. Les appels
existants sont tolérés via `clock_baseline.txt` (« fichier:fonction -> appel », sans numéro de ligne ; cliquet :
aucune nouvelle entrée, une entrée corrigée doit être retirée).

    cd backend && PYTHONPATH=. python3.11 tests/garde_fous/test_clock_guard.py   # régénère la baseline
"""
import ast
from pathlib import Path

APP_DIR = Path(__file__).parents[2] / "app"
BASELINE_PATH = Path(__file__).parent / "clock_baseline.txt"
ALLOWED = {"app/core/time.py"}
_CLOCK_CALLS = {"now", "today", "utcnow"}
_CLOCK_OWNERS = {"datetime", "date"}


def _is_clock_call(node: ast.AST) -> str | None:
    """`datetime.now(...)`, `date.today()`, `datetime.utcnow()` (y compris `datetime.datetime.now`)."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in _CLOCK_CALLS):
        return None
    owner = node.func.value
    owner_name = owner.id if isinstance(owner, ast.Name) else owner.attr if isinstance(owner, ast.Attribute) else None
    return f"{owner_name}.{node.func.attr}()" if owner_name in _CLOCK_OWNERS else None


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scope: list[str] = []
        self.found: set[tuple[str, str]] = set()

    def _enter(self, node: ast.AST) -> None:
        self.scope.append(node.name)  # type: ignore[attr-defined]
        self.generic_visit(node)
        self.scope.pop()

    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = _enter

    def visit_Call(self, node: ast.Call) -> None:
        call = _is_clock_call(node)
        if call:
            self.found.add((".".join(self.scope) or "<module>", call))
        self.generic_visit(node)


def clock_violations(app_dir: Path) -> set[str]:
    found: set[str] = set()
    for path in sorted(app_dir.rglob("*.py")):
        rel = f"app/{path.relative_to(app_dir).as_posix()}"
        if "__pycache__" in path.parts or rel in ALLOWED:
            continue
        visitor = _Visitor()
        visitor.visit(ast.parse(path.read_text(encoding="utf-8")))
        found.update(f"{rel}:{scope} -> {call}" for scope, call in visitor.found)
    return found


def _baseline() -> set[str]:
    return set(BASELINE_PATH.read_text(encoding="utf-8").splitlines()) - {""}


def test_clock_calls_are_detected(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core/time.py").write_text("from datetime import datetime\nx = datetime.now()\n")
    (tmp_path / "s.py").write_text(
        "import datetime as dt\nfrom datetime import datetime, date\n"
        "def f():\n    return datetime.now(), date.today(), datetime.utcnow(), dt.datetime.now()\n"
        "def g(x):\n    return x.now(), utcnow_naive()\n")
    assert clock_violations(tmp_path) == {
        "app/s.py:f -> datetime.now()", "app/s.py:f -> date.today()", "app/s.py:f -> datetime.utcnow()"}


def test_clock_goes_through_core_time():
    found, baseline = clock_violations(APP_DIR), _baseline()
    assert sorted(found - baseline) == [], "appel direct à l'horloge : utiliser app.core.time"
    assert sorted(baseline - found) == [], f"appels corrigés : les retirer de {BASELINE_PATH.name}"


if __name__ == "__main__":
    BASELINE_PATH.write_text("\n".join(sorted(clock_violations(APP_DIR))) + "\n", encoding="utf-8")
    print(f"Baseline écrite : {BASELINE_PATH}")
