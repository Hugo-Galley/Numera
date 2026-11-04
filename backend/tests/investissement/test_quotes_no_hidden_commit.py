"""Enregistrer une cotation ne valide jamais la session de l'appelant."""
import asyncio
from datetime import date

from sqlalchemy.orm import sessionmaker

from app.models.account import Account
from app.models.security_price import SecurityPrice
from app.services.investissement.market import quotes


def test_get_market_quotes_does_not_commit_caller_session(db_session, monkeypatch):
    async def fake_rates(base="EUR"):
        return {"EUR": 1.0}

    async def fake_fetch(client, sym, rates, now):
        return {"price": 10.0, "currency": "EUR", "stale": False}, date(2026, 1, 5), 10.0

    monkeypatch.setattr(quotes, "get_exchange_rates", fake_rates)
    monkeypatch.setattr(quotes, "_fetch_quote", fake_fetch)
    quotes._QUOTES_CACHE.clear()
    db_session.add(Account(name="Titres", type="investissement"))
    db_session.flush()

    asyncio.run(quotes.get_market_quotes(["AAA"], db=db_session))
    assert db_session.query(SecurityPrice).count() == 1  # écrit, mais pas validé
    db_session.rollback()

    fresh = sessionmaker(bind=db_session.get_bind())()
    assert fresh.query(SecurityPrice).count() == 0
    assert fresh.query(Account).count() == 0
