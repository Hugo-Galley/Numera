import ast
from pathlib import Path

SERVER_API = Path(__file__).resolve().parents[3] / "mcp-server" / "server_api.py"
TOOLS = {"get_month_review": "/month-review", "list_month_closures": "/month-review/closures"}


def _functions():
    tree = ast.parse(SERVER_API.read_text())
    return {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}


def _is_mcp_tool(fn: ast.FunctionDef) -> bool:
    return any(ast.unparse(d) == "mcp.tool()" for d in fn.decorator_list)


def test_month_review_tools_are_registered():
    functions = _functions()
    for name in TOOLS:
        assert name in functions, f"outil MCP manquant : {name}"
        assert _is_mcp_tool(functions[name])


def test_month_review_tools_are_read_only_get_calls():
    functions = _functions()
    for name, route in TOOLS.items():
        calls = [
            n for n in ast.walk(functions[name])
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and ast.unparse(n.func.value) == "api"
        ]
        assert calls, f"{name} n'appelle pas l'API"
        assert {c.func.attr for c in calls} == {"get"}
        assert route in ast.unparse(functions[name])
