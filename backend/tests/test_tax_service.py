"""Vue fiscale : le conseil reste disponible quand l'épargne de précaution ne peut pas être calculée."""
import asyncio
from datetime import date

import app.services.tax as tax_service


def test_overview_survives_resilience_failure(db_session, monkeypatch):
    async def broken_resilience(db, year, month):
        raise RuntimeError("résilience indisponible")

    monkeypatch.setattr(tax_service, "compute_resilience", broken_resilience)
    overview = asyncio.run(tax_service.tax_overview(db_session, date(2026, 6, 15)))

    assert overview.precaution_months is None
