"""Profilage des routes GET sur une base de démo volumineuse (skill `numera-performance`).

    cd backend && PYTHONPATH=. python3.11 scripts/perf_profile.py seed --db /tmp/perf_demo.db --months 240 --multiply 6
    cd backend && PYTHONPATH=. python3.11 scripts/perf_profile.py bench --db /tmp/perf_demo.db
    cd backend && PYTHONPATH=. python3.11 scripts/perf_profile.py profile --db /tmp/perf_demo.db /analytics/audit

Le nom du fichier doit contenir « demo » (garde de `DEMO_MODE`) : jamais la vraie base. Le script pose lui-même
`DEMO_MODE`, `DATABASE_URL` et une `SECRET_KEY` jetable avant d'importer l'application.
"""
import argparse
import asyncio
import cProfile
import io
import logging
import os
import pstats
import secrets
import sys
import time
from collections import defaultdict
from pathlib import Path

DUPLICATE_SKIPPED_COLUMNS = {"id", "linked_transaction_id", "linked_investment_transaction_id", "is_transfer"}


def configure(db_path: str) -> None:
    """Environnement de l'application : à appeler avant tout import de `app`."""
    if "demo" not in Path(db_path).name:
        sys.exit("Le nom de la base doit contenir « demo » (garde DEMO_MODE) : jamais la vraie base.")
    os.environ.update(DEMO_MODE="true", DATABASE_URL=f"sqlite:///{db_path}", SECRET_KEY=secrets.token_hex(32))
    logging.disable(logging.CRITICAL)


def seed(db_path: str, months: int, multiply: int) -> None:
    """Base de démo sur `months` mois (≈ 31 transactions par mois), puis dupliquée `multiply` fois."""
    configure(db_path)
    import app.services.systeme.demo.generator as generator
    from app.core.migrations import run_migrations
    from app.db.session import SessionLocal
    from app.services.systeme.demo import generate_demo_data, wipe_database

    generator.DEMO_MONTHS = months
    run_migrations()
    db = SessionLocal()
    try:
        wipe_database(db)
        asyncio.run(generate_demo_data(db))
        if multiply:
            _multiply_transactions(db, multiply)
    finally:
        db.close()
    print(f"Base générée : {db_path}")


def _multiply_transactions(db, copies: int) -> None:
    """Copies décalées de quelques heures (mêmes mois) des transactions non liées, puis soldes recalculés."""
    from sqlalchemy import func, insert, select, update

    from app.models.account import Account
    from app.models.transaction import Transaction
    from app.services.budget.balances import recalculate_running_balances

    table = Transaction.__table__
    columns = [c.name for c in table.columns if c.name not in DUPLICATE_SKIPPED_COLUMNS]
    original_max = db.execute(select(func.max(Transaction.id))).scalar() or 0
    for k in range(1, copies + 1):
        last = db.execute(select(func.max(Transaction.id))).scalar() or 0
        source = select(*[table.c[name] for name in columns]).where(
            Transaction.id <= original_max, Transaction.linked_transaction_id.is_(None), Transaction.is_transfer.is_(False)
        )
        db.execute(insert(table).from_select(columns, source))
        db.execute(update(table).where(table.c.id > last).values(date=func.datetime(table.c.date, f"+{k} hours")))
    for account in db.query(Account).all():
        recalculate_running_balances(db, account.id)
    db.commit()
    print(f"{db.query(Transaction).count()} transactions")


def get_paths() -> list[str]:
    from app.main import app

    return [p for p, ops in app.openapi()["paths"].items() if "get" in ops and "{" not in p and not p.startswith("/api/mcp")]


def authenticated_app():
    from app.controllers.deps import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: "admin"
    return app


def bench(db_path: str, top: int) -> None:
    """Meilleur de deux appels par route GET sans paramètre de chemin (le second profite des caches)."""
    configure(db_path)
    from fastapi.testclient import TestClient

    client = TestClient(authenticated_app(), raise_server_exceptions=False)
    results = []
    for path in get_paths():
        timings = []
        for _ in range(2):
            started = time.perf_counter()
            response = client.get(path)
            timings.append(time.perf_counter() - started)
        results.append((min(timings) * 1000, path, response.status_code, len(response.content) // 1024))
    results.sort(reverse=True)
    for ms, path, status, kb in results[:top]:
        print(f"{ms:8.0f} ms  {status}  {kb:5d} KB  {path}")
    print(f"{len(results)} routes, somme {sum(r[0] for r in results):.0f} ms")


def profile(db_path: str, routes: list[str]) -> None:
    """Pour chaque route : durée, nombre et durée des requêtes SQL, fonctions de l'application les plus coûteuses.

    Les endpoints synchrones sont exécutés dans la boucle (pas de pool de threads) pour que cProfile les voie.
    """
    configure(db_path)
    import fastapi.dependencies.utils as dependency_utils
    import fastapi.routing as routing
    import httpx
    from sqlalchemy import event

    from app.db.session import engine

    async def inline(function, /, *args, **kwargs):
        return function(*args, **kwargs)

    routing.run_in_threadpool = inline
    dependency_utils.run_in_threadpool = inline
    statements: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])

    @event.listens_for(engine, "before_cursor_execute")
    def before(conn, cursor, statement, parameters, context, executemany):
        context._started = time.perf_counter()

    @event.listens_for(engine, "after_cursor_execute")
    def after(conn, cursor, statement, parameters, context, executemany):
        entry = statements[" ".join(statement.split())[:110]]
        entry[0] += 1
        entry[1] += time.perf_counter() - context._started

    async def run() -> None:
        transport = httpx.ASGITransport(app=authenticated_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://perf") as client:
            for route in routes:
                await client.get(route)  # chauffe (imports, caches)
                statements.clear()
                profiler = cProfile.Profile()
                started = time.perf_counter()
                profiler.enable()
                await client.get(route)
                profiler.disable()
                _report(route, time.perf_counter() - started, statements, profiler)

    asyncio.run(run())


def _report(route: str, elapsed: float, statements: dict[str, list[float]], profiler: cProfile.Profile) -> None:
    count = int(sum(v[0] for v in statements.values()))
    sql_ms = sum(v[1] for v in statements.values()) * 1000
    print(f"\n#### {route}  {elapsed * 1000:.0f} ms, {count} requêtes SQL, {sql_ms:.0f} ms en SQL (profileur actif : durées gonflées)")
    stream = io.StringIO()
    pstats.Stats(profiler, stream=stream).sort_stats("cumulative").print_stats(60)
    lines = [line.strip()[-120:] for line in stream.getvalue().splitlines() if "/backend/app/" in line and "main.py" not in line]
    print("\n".join(f"   {line}" for line in lines[:8]))
    for sql, (n, seconds) in sorted(statements.items(), key=lambda item: -item[1][1])[:3]:
        print(f"   SQL {int(n):4d}x {seconds * 1000:6.0f} ms  {sql}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    seed_cmd = sub.add_parser("seed", help="génère une base de démo volumineuse")
    seed_cmd.add_argument("--db", required=True)
    seed_cmd.add_argument("--months", type=int, default=240)
    seed_cmd.add_argument("--multiply", type=int, default=0, help="copies supplémentaires des transactions (6 ≈ 50 000 lignes)")
    bench_cmd = sub.add_parser("bench", help="chronomètre toutes les routes GET")
    bench_cmd.add_argument("--db", required=True)
    bench_cmd.add_argument("--top", type=int, default=20)
    profile_cmd = sub.add_parser("profile", help="profile des routes précises")
    profile_cmd.add_argument("--db", required=True)
    profile_cmd.add_argument("routes", nargs="+")
    args = parser.parse_args()
    if args.command == "seed":
        seed(args.db, args.months, args.multiply)
    elif args.command == "bench":
        bench(args.db, args.top)
    else:
        profile(args.db, args.routes)


if __name__ == "__main__":
    main()
