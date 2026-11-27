"""Audit R3 : les migrations Alembic doivent produire exactement le schéma des modèles.

Les autres tests utilisent `create_all` et ne voient donc pas les dérives de migration : une
installation neuve ou une restauration sur schéma vierge échouait (colonnes manquantes).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text

from app import models  # noqa: F401
from app.db.base import Base

BACKEND = Path(__file__).resolve().parents[2]
PREVIOUS_HEAD = "e3c8a1f5b7d2"  # tête avant la migration de rattrapage


def _alembic(db_url: str, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": db_url, "APP_ENV": "test", "PYTHONPATH": str(BACKEND)}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env, capture_output=True, text=True
    )


def _schema_diffs(db_url: str) -> list:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": False, "render_as_batch": True})
        diffs = compare_metadata(ctx, Base.metadata)
    engine.dispose()
    return diffs


def test_upgrade_head_on_empty_database_matches_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    result = _alembic(url, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    assert _schema_diffs(url) == []


def test_catch_up_is_a_noop_on_a_schema_created_by_create_all(tmp_path):
    """Cas de la prod : base créée par `create_all`, puis marquée à la révision précédente."""
    url = f"sqlite:///{tmp_path / 'prodlike.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO accounts (name, type, currency, active, is_main, created_at, last_verified_at, valuation_mode) "
                          "VALUES ('Courant', 'courant', 'EUR', 1, 0, '2026-01-01', '2026-01-01', 'snapshot')"))
    engine.dispose()

    assert _alembic(url, "stamp", PREVIOUS_HEAD).returncode == 0
    result = _alembic(url, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    assert _schema_diffs(url) == []
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM accounts")).scalar() == 1
    engine.dispose()


def test_migrated_schema_enforces_cascade_deletes(tmp_path):
    """Avec PRAGMA foreign_keys=ON, supprimer un compte supprime ses transactions."""
    url = f"sqlite:///{tmp_path / 'cascade.db'}"
    assert _alembic(url, "upgrade", "head").returncode == 0
    engine = create_engine(url)
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        conn.execute(text("INSERT INTO accounts (id, name, type, currency, active, is_main, created_at, last_verified_at, valuation_mode) "
                          "VALUES (1, 'A', 'courant', 'EUR', 1, 0, '2026-01-01', '2026-01-01', 'snapshot')"))
        conn.execute(text("INSERT INTO transactions (account_id, date, month_label, type, merchant, amount, currency, original_amount, running_balance) "
                          "VALUES (1, '2026-01-02', 'Janvier', 'Sortie', 'X', 5, 'EUR', 5, 0)"))
        conn.execute(text("DELETE FROM accounts WHERE id = 1"))
        assert conn.execute(text("SELECT COUNT(*) FROM transactions")).scalar() == 0
    engine.dispose()


def test_run_migrations_bootstraps_an_empty_database(tmp_path, monkeypatch):
    """Démarrage sur base vierge : run_migrations produit le schéma exact des modèles."""
    from app.core import migrations
    from app.core.config import settings

    url = f"sqlite:///{tmp_path / 'boot.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setattr(settings, "database_url", url)
    migrations.run_migrations()
    assert _schema_diffs(url) == []
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    engine.dispose()


def test_run_migrations_does_not_need_alembic_on_path(tmp_path, monkeypatch):
    """Venv non activé (CI, `uv sync` sans `source`) : `alembic` absent du PATH ne bloque pas le démarrage."""
    from app.core import migrations
    from app.core.config import settings

    url = f"sqlite:///{tmp_path / 'nopath.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(settings, "database_url", url)
    migrations.run_migrations()
    assert _schema_diffs(url) == []


def test_exchange_rate_uniqueness_migration_removes_duplicates(tmp_path):
    url = f"sqlite:///{tmp_path / 'dups.db'}"
    assert _alembic(url, "upgrade", "a7d3f1c9e5b2").returncode == 0
    engine = create_engine(url)
    with engine.begin() as conn:
        for rate in (1.1, 1.2):
            conn.execute(text("INSERT INTO historical_exchange_rates (date, currency, rate) VALUES ('2026-01-05', 'USD', :r)"), {"r": rate})
    engine.dispose()

    result = _alembic(url, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT rate FROM historical_exchange_rates")).fetchall() == [(1.1,)]
    engine.dispose()


# Plancher du test de downgrade : `ece5365a3f43` (marchands) ne se rétrograde pas. Son `downgrade` généré
# automatiquement supprime l'index `ix_bank_connections_id` d'une table (`bank_connections`) que ses propres
# migrations ne créent jamais (elle n'existe que sur d'anciennes bases) → `ValueError: No such index`.
# Exception justifiée : on ne réécrit pas une migration ancienne déjà appliquée en production. Les migrations
# antérieures à ce point ne sont donc pas rejouées vers le bas.
DOWNGRADE_FLOOR = "ece5365a3f43"


def test_downgrade_then_upgrade_head_roundtrip(tmp_path):
    """`upgrade head → downgrade <plancher> → upgrade head` sur base vide : toutes les migrations récentes se rejouent.

    Deux migrations de données ont un `downgrade` volontairement vide (7d3f9a21c8b4, f1b7c4a9d2e6) : elles
    corrigent des données existantes, il n'y a rien à défaire sur une base vide. Toute nouvelle migration dont le
    `downgrade` échoue ou laisse un schéma différent des modèles fait échouer ce test ; si l'irréversibilité est
    inévitable, la nommer ici en exception justifiée (comme `DOWNGRADE_FLOOR`), jamais la contourner en silence.
    """
    url = f"sqlite:///{tmp_path / 'roundtrip.db'}"
    assert _alembic(url, "upgrade", "head").returncode == 0
    down = _alembic(url, "downgrade", DOWNGRADE_FLOOR)
    assert down.returncode == 0, down.stderr
    current = _alembic(url, "current")
    assert DOWNGRADE_FLOOR in current.stdout, current.stdout + current.stderr
    up = _alembic(url, "upgrade", "head")
    assert up.returncode == 0, up.stderr
    assert _schema_diffs(url) == []


def _insert_profile(conn, name, ticker, *, aliases="[]", countries="{}", sectors="{}", top="[]", system=0, isin=None):
    conn.execute(
        text(
            "INSERT INTO etf_profiles (name, ticker, isin, aliases, countries, sectors, top_holdings, composition_sources, is_system, created_at, updated_at) "
            "VALUES (:n, :t, :i, :a, :c, :s, :h, '{}', :sys, '2026-01-01', '2026-01-01')"
        ),
        {"n": name, "t": ticker, "i": isin, "a": aliases, "c": countries, "s": sectors, "h": top, "sys": system},
    )
    return conn.execute(text("SELECT id FROM etf_profiles WHERE name = :n"), {"n": name}).scalar_one()


def test_purge_etf_profiles_migration_cleans_aliases_detaches_and_deletes(tmp_path):
    url = f"sqlite:///{tmp_path / 'purge.db'}"
    assert _alembic(url, "upgrade", "7d2e9b4c1a6f").returncode == 0
    engine = create_engine(url)
    with engine.begin() as conn:
        orphan = _insert_profile(conn, "Orphan", "ORPH", aliases='["ORPH"]')
        held = _insert_profile(conn, "Held", "HELD")
        _insert_profile(conn, "Full", "FULL", sectors='{"Technologie": 50.0}')
        system = _insert_profile(conn, "System", "SYS", system=1, aliases='["SYS"]')
        bad1 = _insert_profile(conn, "Bad1", "BAD1", aliases="not json", sectors='{"Finance": 1.0}')
        bad2 = _insert_profile(conn, "Bad2", "BAD2", aliases='{"a":1}', sectors='{"Finance": 1.0}')
        _insert_profile(conn, "SysEmpty", "SYSE", system=1)
        tx_only = _insert_profile(conn, "TxOnly", "TXO")
        manual = _insert_profile(conn, "Manual", "MAN")
        cisco = _insert_profile(conn, "Cisco CDR", "CSCO.TO", aliases='["CSCO.TO", "CSCO", "CISCO CDR", "CSCO.NEO"]')
        conn.execute(text("INSERT INTO accounts (name, type, currency, active, created_at) VALUES ('CTO', 'investissement', 'EUR', 1, '2026-01-01')"))
        acc = conn.execute(text("SELECT id FROM accounts")).scalar_one()
        conn.execute(
            text("INSERT INTO investment_transactions (account_id, date, type, amount, original_amount, etf_profile_id) VALUES (:a, '2026-01-01', 'achat', 1, 1, :p)"),
            {"a": acc, "p": tx_only},
        )
        for ticker, pid in (("HELD", held), ("CSCO", cisco), ("CSCO.TO", cisco), ("UNRELATED", manual)):
            conn.execute(
                text(
                    "INSERT INTO portfolio_holdings (account_id, ticker, asset_name, quantity, currency, etf_profile_id, created_at, updated_at) "
                    "VALUES (:a, :t, :t, 1, 'EUR', :p, '2026-01-01', '2026-01-01')"
                ),
                {"a": acc, "t": ticker, "p": pid},
            )
    engine.dispose()

    result = _alembic(url, "upgrade", "a8c3e5f1d7b2")
    assert result.returncode == 0, result.stderr
    engine = create_engine(url)
    with engine.connect() as conn:
        names = {r[0] for r in conn.execute(text("SELECT name FROM etf_profiles"))}
        assert names == {"Held", "Full", "System", "Cisco CDR", "Bad1", "Bad2", "SysEmpty", "TxOnly", "Manual"}  # seul le vide orphelin est supprimé
        assert orphan not in {r[0] for r in conn.execute(text("SELECT id FROM etf_profiles"))}
        cisco_aliases = json.loads(conn.execute(text("SELECT aliases FROM etf_profiles WHERE id = :i"), {"i": cisco}).scalar_one())
        assert cisco_aliases == ["CSCO.TO", "CSCO.NEO"]  # alias tronqué et nom en majuscules retirés
        assert conn.execute(text("SELECT aliases FROM etf_profiles WHERE id = :i"), {"i": system}).scalar_one() == '["SYS"]'
        for pid, raw in ((bad1, "not json"), (bad2, '{"a":1}')):  # alias illisibles : intacts, sans plantage
            assert conn.execute(text("SELECT aliases FROM etf_profiles WHERE id = :i"), {"i": pid}).scalar_one() == raw
        links = dict(conn.execute(text("SELECT ticker, etf_profile_id FROM portfolio_holdings")).fetchall())
        assert links == {"HELD": held, "CSCO": None, "CSCO.TO": cisco, "UNRELATED": manual}  # lien manuel gardé ; l'action Cisco est détachée du CDR
    engine.dispose()


def test_etf_constituents_migration_keeps_holdings_linked_to_their_profile(tmp_path):
    """La migration recrée `etf_profiles` : les positions rattachées ne doivent pas être détachées."""
    url = f"sqlite:///{tmp_path / 'constituents.db'}"
    assert _alembic(url, "upgrade", "b4d7f1a9c3e5").returncode == 0
    engine = create_engine(url)
    with engine.begin() as conn:
        profile = _insert_profile(conn, "World", "CW8.PA", sectors='{"Finance": 15.0}', system=1)
        conn.execute(text("INSERT INTO accounts (name, type, currency, active, created_at) VALUES ('PEA', 'investissement', 'EUR', 1, '2026-01-01')"))
        conn.execute(
            text("INSERT INTO portfolio_holdings (account_id, ticker, asset_name, quantity, currency, etf_profile_id, created_at, updated_at) "
                 "VALUES (1, 'CW8.PA', 'World', 1, 'EUR', :p, '2026-01-01', '2026-01-01')"),
            {"p": profile},
        )
    engine.dispose()

    result = _alembic(url, "upgrade", "head")
    assert result.returncode == 0, result.stderr

    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT etf_profile_id FROM portfolio_holdings")).scalar_one() == profile
        row = conn.execute(text("SELECT replication, lines_count, exposure_profile_id FROM etf_profiles WHERE id = :i"), {"i": profile}).one()
        assert tuple(row) == ("unknown", 0, None)
    engine.dispose()


def test_preset_compositions_migration_clears_only_preset_fields(tmp_path):
    url = f"sqlite:///{tmp_path / 'presets.db'}"
    assert _alembic(url, "upgrade", "c6e1a9d4f7b2").returncode == 0
    engine = create_engine(url)
    countries, sectors, top = '{"USA": 70.0}', '{"Finance": 15.0}', '[{"name": "Apple", "weight": 5.0}]'
    cases = {
        "Preset": '{"countries": "preset", "sectors": "preset", "top_holdings": "preset"}',
        "Mixed": '{"countries": "manual", "sectors": "yahoo", "top_holdings": "preset"}',
        "Kept": '{"countries": "manual", "sectors": "ishares"}',
        "Garbage": "pas du json",
    }
    with engine.begin() as conn:
        for name, sources in cases.items():
            pid = _insert_profile(conn, name, name.upper(), countries=countries, sectors=sectors, top=top, system=1)
            conn.execute(text("UPDATE etf_profiles SET composition_sources = :s, composition_refreshed_at = '2026-11-01' WHERE id = :i"),
                         {"s": sources, "i": pid})
    engine.dispose()

    result = _alembic(url, "upgrade", "d8f3b6a1c9e4")
    assert result.returncode == 0, result.stderr

    engine = create_engine(url)
    with engine.connect() as conn:
        rows = {r.name: r for r in conn.execute(text(
            "SELECT name, countries, sectors, top_holdings, composition_sources, composition_refreshed_at FROM etf_profiles"))}
    engine.dispose()

    def state(name):
        r = rows[name]
        return r.countries, r.sectors, r.top_holdings, r.composition_sources, r.composition_refreshed_at is None

    assert state("Preset") == ("{}", "{}", "[]", "{}", True)  # relu au prochain passage
    assert state("Mixed") == (countries, sectors, "[]", '{"countries": "manual", "sectors": "yahoo"}', True)
    assert state("Kept") == (countries, sectors, top, cases["Kept"], False)
    assert state("Garbage") == (countries, sectors, top, "pas du json", False)


def _insert_row(conn, table, **values):
    columns = ", ".join(values)
    params = ", ".join(f":{k}" for k in values)
    conn.execute(text(f"INSERT INTO {table} ({columns}) VALUES ({params})"), values)  # noms fixés par le test


def test_drop_system_etf_profiles_reattaches_and_cleans(tmp_path):
    """`e1b7c4a9f2d6` : chaque position sur le profil de son fonds, plus aucun profil système (règles de
    `domain/etf_attachment.py`), y compris sur les lignes que le rebuild recopie sur les positions."""
    url = f"sqlite:///{tmp_path / 'system.db'}"
    assert _alembic(url, "upgrade", "d8f3b6a1c9e4").returncode == 0
    engine = create_engine(url)
    with engine.begin() as conn:
        world = _insert_profile(conn, "MSCI World", "CW8.PA", isin="LU1681043599", system=1,
                                aliases='["CW8", "CW8.PA", "WPEA.PA", "URTH", "IE0002XZSHO1"]')
        _insert_profile(conn, "S&P 500", "ESE.PA", isin="FR0011550185", system=1, aliases='["ESE.PA"]')
        cac = _insert_profile(conn, "CAC 40", "C40.PA", isin="FR0007054316", system=1, aliases='["C40.PA", "LQQ.PA"]')
        manual = _insert_profile(conn, "Manuel", "MAN.PA", aliases="pas du json")
        reference = _insert_profile(conn, "Référence", "REF.PA", isin="IE00B5BMR087", system=1)
        synthetic = _insert_profile(conn, "Synthétique", "SYN.PA", isin="FR0013412020")
        conn.execute(text("UPDATE etf_profiles SET exposure_profile_id = :r WHERE id = :s"),
                     {"r": reference, "s": synthetic})
        conn.execute(text("INSERT INTO accounts (name, type, currency, active, created_at) VALUES ('PEA', 'investissement', 'EUR', 1, '2026-01-01')"))
        positions = (
            ("IE0002XZSHO1.SG", None, world), ("CW8.PA", None, world), ("XYZ.PA", None, world),
            ("AAA.PA", "IE000BI8OT95", cac), ("AAA.DE", "IE000BI8OT95", world), ("BBB.PA", None, manual),
            ("SOLO.PA", "IE000BI8OT95", None), ("TTE.PA", "FR0000120271", None),
        )
        for ticker, isin, profile in positions:
            _insert_row(conn, "portfolio_holdings", account_id=1, ticker=ticker, isin=isin, asset_name=f"Nom {ticker}",
                        quantity=1, currency="EUR", etf_profile_id=profile, created_at="2026-01-01",
                        updated_at="2026-01-01")
        for ticker, profile in (("XYZ.PA", world), ("CW8.PA", world), ("IE0002XZSHO1.SG", world), (None, cac)):
            _insert_row(conn, "investment_transactions", account_id=1, date="2026-01-01", type="achat", amount=1,
                        original_amount=1, ticker=ticker, etf_profile_id=profile, currency="EUR", is_transfer=0,
                        is_transfer_ignored=0)
        _insert_row(conn, "holding_baseline_items", account_id=1, baseline_date="2026-01-01", ticker="XYZ.PA",
                    asset_name="XYZ", quantity=1, currency="EUR", etf_profile_id=world)
    engine.dispose()

    result = _alembic(url, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    assert _schema_diffs(url) == []

    engine = create_engine(url)
    with engine.connect() as conn:
        profiles = {r.name: r for r in conn.execute(text("SELECT * FROM etf_profiles"))}
        links = dict(conn.execute(text("SELECT ticker, etf_profile_id FROM portfolio_holdings")).fetchall())
        operations = [tuple(r) for r in conn.execute(text(
            "SELECT ticker, etf_profile_id FROM investment_transactions ORDER BY id"))]
        baseline = conn.execute(text("SELECT etf_profile_id FROM holding_baseline_items")).scalar_one()
    engine.dispose()

    by_isin = {p.isin: p for p in profiles.values() if p.isin}
    own, shared = by_isin["IE0002XZSHO1"], by_isin["IE000BI8OT95"]
    assert (own.name, own.ticker, own.composition_refreshed_at) == ("Nom IE0002XZSHO1.SG", "IE0002XZSHO1.SG", None)
    assert (own.countries, own.top_holdings, own.replication, own.lines_count) == ("{}", "[]", "unknown", 0)
    assert links == {
        "IE0002XZSHO1.SG": own.id, "CW8.PA": world, "XYZ.PA": None, "AAA.PA": shared.id, "AAA.DE": shared.id,
        "BBB.PA": manual, "SOLO.PA": shared.id, "TTE.PA": None,
    }
    assert operations == [("XYZ.PA", None), ("CW8.PA", world), ("IE0002XZSHO1.SG", own.id), (None, cac)]
    assert baseline is None
    # « S&P 500 », rattaché à rien, disparaît ; les autres, encore utilisés, ne sont plus « système »
    assert set(profiles) == {"MSCI World", "CAC 40", "Manuel", "Référence", "Synthétique", own.name, shared.name}
    assert not any(p.is_system for p in profiles.values())
    # Les alias livrés qui désignaient d'autres fonds sont retirés, sauf ceux qu'une position utilise encore
    assert json.loads(profiles["MSCI World"].aliases) == ["CW8.PA"]
    assert profiles["Manuel"].aliases == "pas du json"
