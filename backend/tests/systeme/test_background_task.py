"""Tâche de fond : une étape qui échoue ne saute pas les suivantes."""

import asyncio

import pytest

from app import main


class _Stop(Exception):
    pass


def _run_one_cycle(monkeypatch):
    calls = {"sleep": 0}

    async def fake_sleep(_):
        calls["sleep"] += 1
        if calls["sleep"] >= 2:  # 1er : attente du démarrage ; 2e : fin du premier passage
            raise _Stop

    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)
    with pytest.raises(_Stop):
        asyncio.run(main.recurring_transactions_task())


def test_etape_en_echec_ne_saute_pas_les_suivantes(monkeypatch):
    monkeypatch.setattr(main.settings, "DEMO_MODE", False)
    ran: list[str] = []

    class FakeSession:
        def rollback(self):
            ran.append("rollback")

        def close(self):
            pass

    monkeypatch.setattr(main, "SessionLocal", FakeSession)

    async def failing(_db):
        ran.append("recurring")
        raise RuntimeError("boom")

    def ok_sync(name):
        def step(_db):
            ran.append(name)
        return step

    def ok_async(name):
        async def step(_db):
            ran.append(name)
        return step

    monkeypatch.setattr(main, "generate_recurring_transactions", failing)
    monkeypatch.setattr(main, "check_and_generate_pending_salaries", ok_sync("salaries"))
    monkeypatch.setattr(main, "rebuild_due_holdings", ok_async("holdings"))
    monkeypatch.setattr(main, "refresh_held_prices", ok_async("prices"))
    monkeypatch.setattr(main, "refresh_held_etf_profiles", ok_async("etf"))
    monkeypatch.setattr(main, "run_notifications", ok_async("notifications"))

    _run_one_cycle(monkeypatch)

    assert ran == ["recurring", "rollback", "salaries", "holdings", "prices", "etf", "notifications"]
