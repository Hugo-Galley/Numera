"""Règles d'import entre couches (docs/superpowers/specs/2026-10-28-architecture-en-couches-design.md).

Les violations existantes sont tolérées via `architecture_baseline.txt` (cliquet) : aucune nouvelle
violation, et une entrée qui ne se produit plus doit être retirée.

    PYTHONPATH=. python3.11 tests/test_architecture.py   # régénère la baseline
"""
import ast
from pathlib import Path

APP_DIR = Path(__file__).parents[1] / "app"
BASELINE_PATH = Path(__file__).parent / "architecture_baseline.txt"

_DATA_LAYERS_FORBIDDEN = ("app.api", "app.services", "app.repositories", "app.integrations")

FORBIDDEN: dict[str, tuple[str, ...]] = {
    "app.services": ("app.api", "fastapi"),
    "app.repositories": ("app.api", "app.services", "app.integrations", "fastapi"),
    "app.domain": ("app.api", "app.services", "app.repositories", "app.integrations", "app.db", "sqlalchemy.orm", "fastapi"),
    "app.integrations": ("app.api", "app.services", "app.repositories"),
    "app.core": ("app.api",),
    "app.models": _DATA_LAYERS_FORBIDDEN,
    "app.schemas": _DATA_LAYERS_FORBIDDEN,
    "app.db": _DATA_LAYERS_FORBIDDEN,
}


def _matches(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(prefix + ".")


def _module_name(path: Path, app_dir: Path) -> str:
    parts = ["app", *path.relative_to(app_dir).with_suffix("").parts]
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _is_module(name: str, app_dir: Path) -> bool:
    rel = Path(*name.split(".")[1:])
    return (app_dir / rel).with_suffix(".py").exists() or (app_dir / rel / "__init__.py").exists()


def imported_modules(path: Path, module: str, app_dir: Path | None = None) -> set[str]:
    """Modules importés (y compris dans les fonctions), imports relatifs résolus en absolus."""
    app_dir = app_dir or path.parents[len(module.split(".")) - 2]
    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base_parts = package.split(".")[: len(package.split(".")) - (node.level - 1)]
                base = ".".join(base_parts + ([node.module] if node.module else []))
            else:
                base = node.module
            for alias in node.names:
                candidate = f"{base}.{alias.name}"
                found.add(candidate if _matches(candidate, "app") and _is_module(candidate, app_dir) else base)
    return found


def _api_violation(module: str, imported: str) -> bool:
    if not _matches(imported, "app.api") or imported == "app.api.deps":
        return False
    package = module.rpartition(".")[0]
    # Un package peut importer ses propres sous-modules (sous-routers, helpers internes).
    return not (package != "app.api" and _matches(imported, package)) and not _matches(imported, module)


def _commits(path: Path) -> bool:
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "commit"
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
    )


def violations(app_dir: Path) -> set[str]:
    found: set[str] = set()
    for path in sorted(app_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        module = _module_name(path, app_dir)
        rel = f"app/{path.relative_to(app_dir).as_posix()}"
        imported = imported_modules(path, module, app_dir)
        found.update(f"{rel} -> {imp} (introuvable)" for imp in imported
                     if _matches(imp, "app") and imp != "app" and not _is_module(imp, app_dir))
        for layer, forbidden in FORBIDDEN.items():
            if _matches(module, layer):
                found.update(f"{rel} -> {imp}" for imp in imported if any(_matches(imp, f) for f in forbidden))
        if _matches(module, "app.api"):
            found.update(f"{rel} -> {imp}" for imp in imported if _api_violation(module, imp))
        if _matches(module, "app.repositories") and _commits(path):
            found.add(f"{rel} -> commit()")
    return found


def _baseline() -> set[str]:
    return set(BASELINE_PATH.read_text(encoding="utf-8").splitlines()) - {""}


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_relative_imports_are_resolved(tmp_path):
    write(tmp_path / "app/api/analytics/budget.py", "from .utils import x\nfrom ..transactions import y\n")
    write(tmp_path / "app/api/analytics/utils.py", "")
    write(tmp_path / "app/api/transactions.py", "")
    assert imported_modules(tmp_path / "app/api/analytics/budget.py", "app.api.analytics.budget", tmp_path / "app") >= {
        "app.api.analytics.utils", "app.api.transactions"}


def test_local_imports_in_functions_are_found(tmp_path):
    write(tmp_path / "app/core/salary.py", "def f():\n    from app.api.transactions import r\n")
    write(tmp_path / "app/api/transactions.py", "")
    assert "app/core/salary.py -> app.api.transactions" in violations(tmp_path / "app")


def test_api_may_import_deps_and_own_package_only(tmp_path):
    write(tmp_path / "app/api/deps.py", "")
    write(tmp_path / "app/api/accounts.py", "")
    write(tmp_path / "app/api/analytics/__init__.py", "from .budget import router\n")
    write(tmp_path / "app/api/analytics/budget.py", "from app.api.deps import get_db\nfrom .utils import x\n")
    write(tmp_path / "app/api/analytics/utils.py", "")
    write(tmp_path / "app/api/month_review.py", "from app.api import deps\nfrom app.api.accounts import a\n")
    assert violations(tmp_path / "app") == {"app/api/month_review.py -> app.api.accounts"}


def test_services_may_not_import_fastapi(tmp_path):
    write(tmp_path / "app/services/s.py", "from fastapi import HTTPException\n")
    assert violations(tmp_path / "app") == {"app/services/s.py -> fastapi"}


def test_import_of_missing_app_module_is_a_violation(tmp_path):
    """Un import relatif déplacé tel quel pointe vers un module inexistant (souvent avalé par un except)."""
    write(tmp_path / "app/services/audit.py", "def f():\n    from .subscriptions import price_change_id\n")
    write(tmp_path / "app/core/finance.py", "def g():\n    pass\n")
    write(tmp_path / "app/services/ok.py", "from app.core.finance import g\nfrom app import core\n")
    assert violations(tmp_path / "app") == {"app/services/audit.py -> app.services.subscriptions (introuvable)"}


def test_repository_commit_is_a_violation(tmp_path):
    write(tmp_path / "app/repositories/r.py", "def f(db):\n    db.commit()\n")
    assert "app/repositories/r.py -> commit()" in violations(tmp_path / "app")


def test_layers_match_baseline():
    found = violations(APP_DIR)
    baseline = _baseline()
    assert sorted(found - baseline) == [], "nouvelles violations de couches"
    assert sorted(baseline - found) == [], f"violations corrigées : les retirer de {BASELINE_PATH.name}"


if __name__ == "__main__":
    BASELINE_PATH.write_text("\n".join(sorted(violations(APP_DIR))) + "\n", encoding="utf-8")
    print(f"Baseline écrite : {BASELINE_PATH}")
