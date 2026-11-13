"""Un `except Exception` ne doit pas avaler une erreur en silence.

Admis sans condition : le handler relance (`raise`) ou journalise la trace (`logger.exception`, `exc_info=True`) :
c'est la frontière d'une tâche de fond, d'une route ou d'une intégration externe. Sinon l'erreur disparaît dans un
simple avertissement : préférer l'exception précise (`ValueError`, `SQLAlchemyError`, `httpx.HTTPError`…).
Les handlers existants de ce second type sont comptés par fichier dans `broad_except_baseline.json` (cliquet :
le compteur ne monte pas, un fichier corrigé est retiré).

    cd backend && PYTHONPATH=. python3.12 tests/garde_fous/test_broad_except_guard.py   # régénère la baseline
"""
import ast
import json
from pathlib import Path

APP_DIR = Path(__file__).parents[2] / "app"
BASELINE_PATH = Path(__file__).parents[3] / "scripts/quality/baselines/broad_except_baseline.json"
_LOG_METHODS = {"exception"}


def _is_broad(handler: ast.ExceptHandler) -> bool:
    t = handler.type
    return t is None or (isinstance(t, ast.Name) and t.id in {"Exception", "BaseException"})


def _keeps_trace(handler: ast.ExceptHandler) -> bool:
    for node in ast.walk(ast.Module(body=handler.body, type_ignores=[])):
        if isinstance(node, ast.Raise):
            return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in _LOG_METHODS:
                return True
            if any(k.arg == "exc_info" for k in node.keywords):
                return True
    return False


def silent_broad_excepts(app_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted(app_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        n = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler) and _is_broad(node) and not _keeps_trace(node))
        if n:
            counts[f"app/{path.relative_to(app_dir).as_posix()}"] = n
    return counts


def test_silent_broad_excepts_are_detected(tmp_path):
    (tmp_path / "a.py").write_text(
        "def f():\n"
        "    try: x()\n    except Exception: pass\n"            # silencieux
        "    try: x()\n    except Exception: logger.exception('m')\n"  # trace gardée
        "    try: x()\n    except Exception: raise\n"             # relancé
        "    try: x()\n    except Exception as e: logger.warning('m', exc_info=True)\n"
        "    try: x()\n    except ValueError: pass\n")           # précis
    assert silent_broad_excepts(tmp_path) == {"app/a.py": 1}


def test_no_new_silent_broad_except():
    found = silent_broad_excepts(APP_DIR)
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    worse = {f: n for f, n in found.items() if n > baseline.get(f, 0)}
    assert worse == {}, "`except Exception` qui avale l'erreur : exception précise, ou relancer / `logger.exception`"
    better = {f: n for f, n in baseline.items() if found.get(f, 0) < n}
    assert better == {}, f"handlers corrigés : abaisser ou retirer ces entrées de {BASELINE_PATH.name}"


if __name__ == "__main__":
    BASELINE_PATH.write_text(json.dumps(silent_broad_excepts(APP_DIR), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Baseline écrite : {BASELINE_PATH}")
