"""L'étape « ISIN » de la boucle horaire interroge les mêmes émetteurs que les compositions (cache des catalogues partagé)."""
import asyncio

from app import main
from app.integrations.etf_providers.ishares import IShares


def test_hourly_isin_step_shares_the_issuer_instances(monkeypatch):
    seen: dict[str, object] = {}

    async def fake_resolve(db, catalogs=None):
        seen["catalogs"] = catalogs
        return 0

    monkeypatch.setattr(main, "resolve_missing_isins", fake_resolve)
    asyncio.run(main.resolve_isins_step(None))
    assert seen["catalogs"] is main._ISIN_CATALOGS
    assert IShares in [type(c) for c in seen["catalogs"]]
