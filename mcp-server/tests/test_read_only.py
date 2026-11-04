"""Garde-fou : le serveur MCP est en lecture seule, chaque outil n'appelle l'API qu'en GET."""
import ast
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "numera_mcp" / "tools"
MONTH_REVIEW = {"get_month_review": "/month-review", "list_month_closures": "/month-review/closures"}


def _functions() -> dict[str, ast.FunctionDef]:
    found = {}
    for path in sorted(TOOLS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text())
        found.update({n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)})
    return found


def _api_methods(fn: ast.FunctionDef) -> set[str]:
    return {
        n.func.attr
        for n in ast.walk(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and ast.unparse(n.func.value) == "api"
    }


def test_every_api_call_is_a_get():
    for path in TOOLS_DIR.glob("*.py"):
        tree = ast.parse(path.read_text())
        for fn in (n for n in tree.body if isinstance(n, ast.FunctionDef)):
            assert _api_methods(fn) <= {"get"}, f"{path.name}::{fn.name} appelle l'API autrement qu'en GET"


def test_month_review_tools_call_their_route_with_get():
    functions = _functions()
    for name, route in MONTH_REVIEW.items():
        assert _api_methods(functions[name]) == {"get"}
        assert route in ast.unparse(functions[name])
