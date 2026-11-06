"""Règles d'import entre couches (cf. ARCHITECTURE.md § Couches backend).

Les violations existantes sont tolérées via `architecture_baseline.txt` (cliquet) : aucune nouvelle
violation, et une entrée qui ne se produit plus doit être retirée.

    cd backend && PYTHONPATH=. python3.11 tests/garde_fous/test_architecture.py   # régénère la baseline

Contrôles (chaque entrée de la baseline est « fichier -> cause ») :
- imports interdits par couche (`FORBIDDEN`), dont controllers -> models|repositories|db|integrations|domain ;
- `commit()` hors `services/` (et hors tests) : controllers, repositories, core, db, integrations, domain ;
- `db.query(...)` / `db.execute(...)` directs dans `services/` (à déplacer dans un repository) ;
- `async def` sans `await` hors `controllers/` (couvert côté controllers par `test_async_endpoints.py`) ;
- `HTTPException` : un service n'importe ni `fastapi` ni `starlette`.
"""
import ast
from pathlib import Path

APP_DIR = Path(__file__).parents[2] / "app"
BASELINE_PATH = Path(__file__).parent / "architecture_baseline.txt"  # règles historiques d'imports : vide
# Règles ajoutées ensuite (commit hors services, controllers -> models/db…, requêtes dans les services, async inutile) :
# baseline séparée, initialisée sur l'existant. Les deux fichiers sont protégés par le check « Cliquets ».
RULES_BASELINE_PATH = Path(__file__).parent / "architecture_rules_baseline.txt"

_DATA_LAYERS_FORBIDDEN = ("app.controllers", "app.services", "app.repositories", "app.integrations")

FORBIDDEN: dict[str, tuple[str, ...]] = {
    # Un controller ne parle qu'aux services et aux schémas : pas d'ORM, de requêtes, de calculs ni d'appels externes.
    "app.controllers": ("app.models", "app.repositories", "app.db", "app.integrations", "app.domain"),
    "app.services": ("app.controllers", "fastapi", "starlette"),
    "app.repositories": ("app.controllers", "app.services", "app.integrations", "fastapi"),
    "app.domain": ("app.controllers", "app.services", "app.repositories", "app.integrations", "app.db", "sqlalchemy.orm", "fastapi",
                   "app.models", "app.schemas"),
    "app.integrations": ("app.controllers", "app.services", "app.repositories", "app.models", "app.db"),
    # core n'importe que core, models et db (transverse).
    "app.core": ("app.controllers", "app.services", "app.repositories", "app.domain", "app.integrations", "app.schemas", "fastapi"),
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


def _controllers_violation(module: str, imported: str) -> bool:
    if not _matches(imported, "app.controllers") or imported == "app.controllers.deps":
        return False
    parts = module.split(".")
    # Un package de domaine (`app.controllers.<domaine>`) peut importer ses propres modules
    # (sous-routers, helpers internes), jamais ceux d'un autre domaine.
    domain = ".".join(parts[:3]) if len(parts) > 3 else None
    return not (domain and _matches(imported, domain)) and not _matches(imported, module)


# Couches où `commit()` est interdit : seuls les services valident la transaction.
_NO_COMMIT_LAYERS = ("app.controllers", "app.repositories", "app.core", "app.db", "app.integrations", "app.domain")


def _calls_method(tree: ast.AST, *names: str) -> bool:
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in names
        for node in ast.walk(tree)
    )


def _direct_queries(tree: ast.AST) -> bool:
    """`db.query(...)` / `db.execute(...)` (ou `session.…`) : requête écrite hors repository."""
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("query", "execute")
        and isinstance(node.func.value, ast.Name) and node.func.value.id in ("db", "session")
        for node in ast.walk(tree)
    )


def _async_without_await(tree: ast.AST) -> list[str]:
    return [
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef)
        and not any(isinstance(n, (ast.Await, ast.AsyncFor, ast.AsyncWith)) for n in ast.walk(node))
    ]


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
        if _matches(module, "app.controllers"):
            found.update(f"{rel} -> {imp}" for imp in imported if _controllers_violation(module, imp))
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(_matches(module, layer) for layer in _NO_COMMIT_LAYERS) and _calls_method(tree, "commit"):
            found.add(f"{rel} -> commit()")
        if _matches(module, "app.services") and _direct_queries(tree):
            found.add(f"{rel} -> db.query/execute (requête hors repository)")
        if not _matches(module, "app.controllers"):
            found.update(f"{rel} -> async def {name} sans await" for name in _async_without_await(tree))
    return found


def _baseline() -> set[str]:
    lines = BASELINE_PATH.read_text(encoding="utf-8").splitlines() + RULES_BASELINE_PATH.read_text(encoding="utf-8").splitlines()
    return set(lines) - {""}


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_relative_imports_are_resolved(tmp_path):
    write(tmp_path / "app/controllers/analytics/budget.py", "from .utils import x\nfrom ..transactions import y\n")
    write(tmp_path / "app/controllers/analytics/utils.py", "")
    write(tmp_path / "app/controllers/transactions.py", "")
    assert imported_modules(tmp_path / "app/controllers/analytics/budget.py", "app.controllers.analytics.budget", tmp_path / "app") >= {
        "app.controllers.analytics.utils", "app.controllers.transactions"}


def test_local_imports_in_functions_are_found(tmp_path):
    write(tmp_path / "app/core/salary.py", "def f():\n    from app.controllers.transactions import r\n")
    write(tmp_path / "app/controllers/transactions.py", "")
    assert "app/core/salary.py -> app.controllers.transactions" in violations(tmp_path / "app")


def test_controllers_may_import_deps_and_own_package_only(tmp_path):
    write(tmp_path / "app/controllers/deps.py", "")
    write(tmp_path / "app/controllers/accounts.py", "")
    write(tmp_path / "app/controllers/analytics/__init__.py", "from .budget import router\n")
    write(tmp_path / "app/controllers/analytics/budget.py", "from app.controllers.deps import get_db\nfrom .utils import x\n")
    write(tmp_path / "app/controllers/analytics/utils.py", "")
    write(tmp_path / "app/controllers/month_review.py", "from app.controllers import deps\nfrom app.controllers.accounts import a\n")
    assert violations(tmp_path / "app") == {"app/controllers/month_review.py -> app.controllers.accounts"}


def test_controllers_may_import_deps_and_own_domain_only(tmp_path):
    write(tmp_path / "app/controllers/deps.py", "")
    write(tmp_path / "app/controllers/comptes/accounts.py", "")
    write(tmp_path / "app/controllers/budget/transactions.py", "")
    write(tmp_path / "app/controllers/budget/month_review.py",
          "from app.controllers.deps import get_db\nfrom app.controllers.budget.transactions import t\n"
          "from app.controllers.comptes.accounts import a\n")
    write(tmp_path / "app/controllers/budget/salary/config.py", "from app.controllers.budget.transactions import t\n")
    assert violations(tmp_path / "app") == {"app/controllers/budget/month_review.py -> app.controllers.comptes.accounts"}


def test_core_imports_only_core_models_db(tmp_path):
    write(tmp_path / "app/services/s.py", "")
    write(tmp_path / "app/schemas/y.py", "")
    write(tmp_path / "app/models/m.py", "")
    write(tmp_path / "app/db/session.py", "")
    write(tmp_path / "app/core/config.py", "")
    write(tmp_path / "app/core/x.py", "from app.services.s import f\nfrom app.schemas.y import Y\nfrom app.models.m import M\n"
          "from app.db.session import get_db\nfrom app.core.config import settings\n")
    assert violations(tmp_path / "app") == {"app/core/x.py -> app.services.s", "app/core/x.py -> app.schemas.y"}


def test_services_may_not_import_fastapi(tmp_path):
    write(tmp_path / "app/services/s.py", "from fastapi import HTTPException\n")
    assert violations(tmp_path / "app") == {"app/services/s.py -> fastapi"}


def test_import_of_missing_app_module_is_a_violation(tmp_path):
    """Un import relatif déplacé tel quel pointe vers un module inexistant (souvent avalé par un except)."""
    write(tmp_path / "app/services/audit.py", "def f():\n    from .subscriptions import price_change_id\n")
    write(tmp_path / "app/core/finance.py", "def g():\n    pass\n")
    write(tmp_path / "app/services/ok.py", "from app.core.finance import g\nfrom app import core\n")
    assert violations(tmp_path / "app") == {"app/services/audit.py -> app.services.subscriptions (introuvable)"}


def test_services_may_not_import_controllers(tmp_path):
    write(tmp_path / "app/controllers/deps.py", "")
    write(tmp_path / "app/services/s.py", "from app.controllers.deps import get_db\n")
    assert violations(tmp_path / "app") == {"app/services/s.py -> app.controllers.deps"}


def test_repository_commit_is_a_violation(tmp_path):
    write(tmp_path / "app/repositories/r.py", "def f(db):\n    db.commit()\n")
    assert "app/repositories/r.py -> commit()" in violations(tmp_path / "app")


def test_controllers_may_not_reach_data_or_domain_layers(tmp_path):
    for name in ("models/m", "repositories/r", "db/session", "integrations/i", "domain/d", "services/s", "schemas/y", "core/c"):
        write(tmp_path / f"app/{name}.py", "")
    write(tmp_path / "app/controllers/c.py",
          "from app.models.m import M\nfrom app.repositories.r import R\nfrom app.db.session import S\n"
          "from app.integrations.i import I\nfrom app.domain.d import D\n"
          "from app.services.s import ok\nfrom app.schemas.y import ok\nfrom app.core.c import ok\n")
    assert violations(tmp_path / "app") == {
        f"app/controllers/c.py -> app.{m}" for m in ("models.m", "repositories.r", "db.session", "integrations.i", "domain.d")}


def test_lower_layers_forbidden_imports(tmp_path):
    for name in ("models/m", "schemas/y", "db/session"):
        write(tmp_path / f"app/{name}.py", "")
    write(tmp_path / "app/core/x.py", "from fastapi import HTTPException\n")
    write(tmp_path / "app/domain/d.py", "from app.models.m import M\nfrom app.schemas.y import Y\n")
    write(tmp_path / "app/integrations/i.py", "from app.models.m import M\nfrom app.db.session import S\n")
    write(tmp_path / "app/services/s.py", "from starlette.exceptions import HTTPException\n")
    assert violations(tmp_path / "app") == {
        "app/core/x.py -> fastapi",
        "app/domain/d.py -> app.models.m", "app/domain/d.py -> app.schemas.y",
        "app/integrations/i.py -> app.models.m", "app/integrations/i.py -> app.db.session",
        "app/services/s.py -> starlette.exceptions"}


def test_commit_is_forbidden_outside_services(tmp_path):
    for layer in ("controllers", "core", "db", "integrations", "domain", "services"):
        write(tmp_path / f"app/{layer}/m.py", "def f(db):\n    db.commit()\n")
    assert violations(tmp_path / "app") == {
        f"app/{layer}/m.py -> commit()" for layer in ("controllers", "core", "db", "integrations", "domain")}


def test_services_may_not_query_directly(tmp_path):
    write(tmp_path / "app/services/s.py", "def f(db):\n    db.query(1)\n    db.execute(2)\n")
    write(tmp_path / "app/services/ok.py", "def f(repo):\n    repo.query(1)\n")
    assert violations(tmp_path / "app") == {"app/services/s.py -> db.query/execute (requête hors repository)"}


def test_async_without_await_outside_controllers(tmp_path):
    write(tmp_path / "app/services/s.py", "async def bad():\n    return 1\n\nasync def good(x):\n    await x\n")
    write(tmp_path / "app/controllers/c.py", "async def bad():\n    return 1\n")
    assert violations(tmp_path / "app") == {"app/services/s.py -> async def bad sans await"}


def test_layers_match_baseline():
    found = violations(APP_DIR)
    baseline = _baseline()
    assert sorted(found - baseline) == [], "nouvelles violations de couches"
    assert sorted(baseline - found) == [], f"violations corrigées : les retirer de {RULES_BASELINE_PATH.name}"


if __name__ == "__main__":
    RULES_BASELINE_PATH.write_text("\n".join(sorted(violations(APP_DIR))) + "\n", encoding="utf-8")
    print(f"Baseline écrite : {RULES_BASELINE_PATH}")
