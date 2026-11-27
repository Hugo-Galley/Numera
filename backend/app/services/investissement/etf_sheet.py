"""Fiche d'un ETF : identité, répartitions, toutes les lignes et valeur détenue.

Nombre de requêtes constant : les lignes sont lues en une fois, par colonnes."""
import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.i18n import tr
from app.domain.etf_profiles import SOURCE_MANUAL, load_sources, to_read
from app.domain.etf_sheet import aggregate_weights, exposure_eur, stored_weights
from app.domain.holdings import holding_price_eur
from app.integrations.currency import get_exchange_rates
from app.models.etf_profile import EtfProfile
from app.repositories.investissement import etf_constituents
from app.repositories.investissement import etf_profiles as repo
from app.repositories.investissement import holdings as holdings_repo
from app.schemas.etf_sheet import EtfSheet, EtfSheetLine, WeightRow
from app.services.investissement.market import quotes as market_quotes


async def _held_value_eur(db: Session, profile_id: int) -> float:
    """Valeur des positions à soi rattachées au fonds, valorisées comme par le scanner de diversification."""
    positions = holdings_repo.own_positions_of_profile(db, profile_id)
    if not positions:
        return 0.0
    quotes = await market_quotes.get_market_quotes([ticker for ticker, *_ in positions], db=db)
    market_quotes.persist_fetched_prices(db)
    rates = await get_exchange_rates("EUR")
    return round(sum(
        round(quantity * holding_price_eur(quotes.get(ticker.upper(), {}).get("price_eur", 0.0), pru, currency, rates), 2)
        for ticker, quantity, pru, currency in positions
    ), 2)


def _top_holdings(profile: EtfProfile) -> list[dict[str, Any]]:
    try:
        values = json.loads(profile.top_holdings or "[]")
    except ValueError:
        return []
    return [v for v in values if isinstance(v, dict)] if isinstance(values, list) else []


async def etf_sheet(db: Session, profile_id: int) -> EtfSheet:
    profile = repo.get(db, profile_id)
    if not profile:
        raise NotFoundError(tr("errors.etf_profile_not_found"))
    reference = repo.get(db, profile.exposure_profile_id) if profile.exposure_profile_id else None
    exposure = reference or profile
    lines = etf_constituents.for_profiles(db, [exposure.id]).get(exposure.id, [])
    # Comme le scanner : une saisie manuelle du fonds détenu l'emporte, champ par champ
    manual = {name for name, origin in load_sources(profile).items() if origin == SOURCE_MANUAL}

    def weights(field: str, attribute: str) -> list[WeightRow]:
        if field not in manual and lines:
            rows = aggregate_weights(lines, attribute)
        else:
            rows = stored_weights(getattr(profile if field in manual else exposure, field))
        return [WeightRow(name=name, weight=weight) for name, weight in rows]

    sheet = EtfSheet(
        profile=to_read(profile, reference.name if reference else None),
        exposure_profile_id=reference.id if reference else None,
        exposure_profile_name=reference.name if reference else None,
        provider=exposure.provider,
        composition_as_of=exposure.composition_as_of,
        coverage_pct=exposure.coverage_pct or 0.0,
        lines_count=exposure.lines_count,
        has_full_list=bool(lines),
        held_value_eur=0.0,
        countries=weights("countries", "country"),
        sectors=weights("sectors", "sector"),
        lines=[EtfSheetLine.model_validate(x) for x in sorted(lines, key=lambda x: -x.weight)],
        top_holdings=[] if lines else _top_holdings(profile if "top_holdings" in manual else exposure),
    )
    # En dernier : valider les cours lus expirerait les profils chargés ci-dessus
    held = sheet.held_value_eur = await _held_value_eur(db, profile_id)
    for line in sheet.lines:
        line.exposure_eur = exposure_eur(line.weight, held)
    sheet.top_holdings = [{**x, "exposure_eur": exposure_eur(x.get("weight"), held)} for x in sheet.top_holdings]
    return sheet
