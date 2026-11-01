"""Un endpoint `async def` sans `await` bloque la boucle d'événements pour rien : il doit être un `def`."""
import ast
from pathlib import Path

CONTROLLERS = Path(__file__).resolve().parents[2] / "app" / "controllers"


def test_no_async_endpoint_without_await():
    offenders = []
    for path in sorted(CONTROLLERS.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.AsyncFunctionDef) and not any(
                isinstance(n, (ast.Await, ast.AsyncFor, ast.AsyncWith)) for n in ast.walk(node)
            ):
                offenders.append(f"{path.relative_to(CONTROLLERS)}:{node.lineno} {node.name}")
    assert offenders == [], "async def sans await (utiliser def) : " + ", ".join(offenders)
