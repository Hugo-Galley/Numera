"""Scanner de diversification : expositions réelles par transparence des ETF, vrais doublons, corrélations,
paris indépendants et écart à une référence de marché (score et alertes), rapportés au portefeuille boursier et
au patrimoine total. Modèle : spec sur-exposition ; calculs dans `domain/exposure/`, vue de risque dans
`diversity_risk`."""
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.i18n import tr
from app.core.logging import get_logger
from app.core.time import utcnow_naive
from app.domain.diversity import Exposure, LookThrough, exposure_rows, look_through, top_companies
from app.domain.diversity_score import score_label
from app.domain.etf_composition import EtfConstituentRow, EtfLine
from app.domain.etf_normalize import index_for_fund_name
from app.domain.etf_profiles import match_profile
from app.domain.exposure.alerts import market_alerts
from app.domain.exposure.correlation import composition_vector
from app.domain.exposure.identity import Holding, Kind, group_exposures
from app.domain.exposure.report import concentration_payload, exposures_payload, market_payload, with_market_pct
from app.domain.holdings import holding_price_eur, holding_profile, is_crypto, is_etf_holding, is_fund
from app.domain.isin import IsinCandidate, pick_isin
from app.integrations import yahoo_finance
from app.integrations.currency import get_exchange_rates
from app.models.account import Account
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding
from app.models.security import Security
from app.repositories.analytics import diversity as repo
from app.repositories.analytics import investments as investments_repo
from app.repositories.comptes.balances import active_accounts
from app.repositories.investissement import etf_constituents
from app.repositories.investissement import etf_profiles as etf_repo
from app.repositories.investissement import securities as securities_repo
from app.services.analytics.diversity_risk import RiskView, pairs_by_source, risk_view, same_fund_rule, weekly_returns_eur
from app.services.comptes.wealth import account_values
from app.services.investissement.etf_profiles import auto_decompose_and_create_profile
from app.services.investissement.market import quotes as market_quotes
from app.services.investissement.market_reference import market_reference

logger = get_logger(__name__)

PROFILE_RETRY = timedelta(days=7)


async def _resolve_profile(db: Session, h: PortfolioHolding, q: dict[str, Any],
                           profiles: list[EtfProfile]) -> EtfProfile | None:
    """Profil ETF de la position : rattaché, retrouvé (correspondance exacte), ou créé depuis Yahoo pour un fonds
    inconnu (seulement si le type du titre est un fonds ; rattachement commité)."""
    matched_p = holding_profile(profiles, h.etf_profile_id, h.ticker, h.isin)
    if matched_p and h.etf_profile_id:
        return matched_p
    if not matched_p and is_fund(q.get("type"), h.ticker):
        try:
            matched_p = await auto_decompose_and_create_profile(db, symbol=h.ticker, name=h.asset_name, isin=h.isin)
        except Exception as e:
            logger.warning(f"Could not auto-decompose {h.ticker}: {e}")
    if not matched_p:
        return None
    try:
        h.etf_profile_id = matched_p.id
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    return matched_p


async def _value_holdings(db: Session, holdings: list[PortfolioHolding], quotes: dict[str, Any],
                          fx_rates: dict[str, Any]) -> tuple[list[dict[str, Any]], float]:
    """Valeur EUR de chaque position (repli sur le PRU sans cours connu) et total du portefeuille boursier."""
    total_stocks_eur = 0.0
    valued_holdings = []
    profiles = etf_repo.all_profiles(db)
    for h in holdings:
        q = quotes.get(h.ticker.upper(), {})
        price_eur = holding_price_eur(q.get("price_eur", 0.0), h.buy_price_avg, h.currency, fx_rates)

        profile = await _resolve_profile(db, h, q, profiles)
        val_eur = round(h.quantity * price_eur, 2)
        total_stocks_eur += val_eur
        valued_holdings.append({
            "id": h.id,
            "account_id": h.account_id,
            "ticker": h.ticker,
            "isin": h.isin,
            "name": h.asset_name,
            "quantity": h.quantity,
            "price_eur": price_eur,
            "value_eur": val_eur,
            "etf_profile_id": profile.id if profile else None,
            "quote_type": q.get("type"),
            "is_etf": is_etf_holding(q.get("type"), h.ticker, h.isin, profile),
        })
    return valued_holdings, total_stocks_eur


def _is_direct_stock(vh: dict[str, Any]) -> bool:
    return not vh["etf_profile_id"] and not vh["is_etf"] and not is_crypto(vh.get("quote_type"), vh["ticker"])


def _needs_yahoo(security: Security | None) -> bool:
    """Titre absent, ou sans pays ni secteur et pas interrogé depuis `PROFILE_RETRY` (404 de Yahoo mémorisé)."""
    if security is None:
        return True
    if security.country is not None or security.sector is not None:
        return False
    return security.updated_at < utcnow_naive() - PROFILE_RETRY


async def _enrich_from_yahoo(db: Session, holdings: list[dict[str, Any]], found: dict[str, Security]) -> bool:
    """Interroge Yahoo une fois par titre à compléter ; un titre inconnu de Yahoo est mémorisé (ligne sans pays ni
    secteur) pour ne pas être redemandé à chaque scan. Yahoo injoignable : on s'arrête, rien n'est mémorisé."""
    rows = []
    for vh in holdings:
        if not _needs_yahoo(found.get(vh["isin"])):
            continue
        try:
            profile = await yahoo_finance.fetch_asset_profile(vh["ticker"])
        except yahoo_finance.YahooUnavailable as e:
            logger.warning(f"Profil Yahoo indisponible pour {vh['ticker']}: {e}")
            break
        rows.append({"isin": vh["isin"], "ticker": vh["ticker"].upper().split(".")[0], "exchange": None,
                     "name": vh["name"], "country": (profile or {}).get("country"),
                     "sector": (profile or {}).get("sector"), "source": "yahoo"})
    if not rows:
        return False
    try:
        securities_repo.upsert_many(db, rows)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        return False
    return True


def _securities_without_isin(db: Session, holdings: list[dict[str, Any]]) -> dict[str, Security]:
    """Titre d'une position sans ISIN : le seul ISIN de ticker exact et de place compatible (`pick_isin`)."""
    tickers = {vh["ticker"].upper().split(".")[0] for vh in holdings}
    by_ticker: dict[str, list[Security]] = {}
    for sec in securities_repo.by_tickers(db, tickers):
        by_ticker.setdefault(sec.ticker.upper(), []).append(sec)
    result: dict[str, Security] = {}
    for vh in holdings:
        candidates = by_ticker.get(vh["ticker"].upper().split(".")[0], [])
        isin = pick_isin(vh["ticker"], [IsinCandidate(c.isin, c.ticker, c.exchange) for c in candidates])
        match = next((c for c in candidates if c.isin == isin), None)
        if match:
            result[vh["ticker"].upper()] = match
    return result


async def _direct_securities(db: Session, valued_holdings: list[dict[str, Any]]) -> dict[str, Security]:
    """Titres des actions en direct : par ISIN, ou par ticker (clé = ticker de la position) pour une position sans ISIN.

    Yahoo ne sert que les positions avec ISIN (une fois par titre, un seul commit)."""
    direct = [vh for vh in valued_holdings if vh["value_eur"] > 0 and _is_direct_stock(vh)]
    with_isin = [vh for vh in direct if vh.get("isin")]
    found = securities_repo.by_isins(db, [vh["isin"] for vh in with_isin])
    if await _enrich_from_yahoo(db, with_isin, found):
        found = securities_repo.by_isins(db, [vh["isin"] for vh in with_isin])
    return {**found, **_securities_without_isin(db, [vh for vh in direct if not vh.get("isin")])}


async def _wealth_context(db: Session, accounts: list[Account]) -> dict[str, float]:
    """« Ce qu'on a à côté » : épargne, courant, fonds euros des assurances-vie et autres comptes, en EUR.

    Valeurs par `account_values` (source unique, même patrimoine que `patrimoine-allocation`)."""
    totals = {"epargne": 0.0, "courant": 0.0, "fonds_euros": 0.0, "other": 0.0}
    values = await account_values(db, accounts)
    for acc in accounts:
        val_acc_eur = values[acc.id].value_eur
        if acc.type == "epargne":
            totals["epargne"] += val_acc_eur
        elif acc.type == "courant":
            totals["courant"] += val_acc_eur
        elif acc.type == "assurance_vie":
            totals["fonds_euros"] += val_acc_eur * ((acc.fonds_euros_pct or 0.0) / 100.0)
        elif acc.type != "investissement":
            totals["other"] += val_acc_eur
    return totals


async def _accounts_value(db: Session, account_id: int | None) -> float:
    """Valeur des comptes d'investissement du périmètre (EUR), même source que la répartition par compte
    (`account_values`) : positions, espèces, fonds euros et comptes sans position compris."""
    accounts = investments_repo.investment_accounts(db, account_id)
    values = await account_values(db, accounts)
    return sum(values[acc.id].value_eur for acc in accounts)



@dataclass(frozen=True)
class _Compositions:
    """Profil de chaque position (par id de position valorisée) et lignes des profils exposés, chargés une fois."""

    held: dict[int, EtfProfile | None]
    by_id: dict[int, EtfProfile]
    lines: dict[int, list[EtfConstituentRow]]

    def exposed_by(self, profile: EtfProfile) -> EtfProfile:
        """Un synthétique est décrit par la référence physique de son indice."""
        return self.by_id.get(profile.exposure_profile_id or 0, profile)

    def lines_of(self, profile: EtfProfile | None) -> Sequence[EtfLine]:
        return self.lines.get(self.exposed_by(profile).id, []) if profile else []


def _compositions(db: Session, valued_holdings: list[dict[str, Any]]) -> _Compositions:
    profiles = etf_repo.all_profiles(db)
    by_id = {p.id: p for p in profiles}
    held = {
        vh["id"]: by_id.get(vh["etf_profile_id"])
        or match_profile(profiles, vh["ticker"], vh.get("isin"), vh.get("name"))
        for vh in valued_holdings
    }
    exposed = {by_id.get(p.exposure_profile_id or 0, p).id for p in held.values() if p}
    return _Compositions(held, by_id, etf_constituents.for_profiles(db, exposed))


def _look_through(comp: _Compositions, valued_holdings: list[dict[str, Any]],
                  securities: dict[str, Security]) -> LookThrough:
    """Transparence des ETF ; un synthétique est décomposé par la référence de son indice."""

    def exposure_for(profile: EtfProfile) -> Exposure:
        return Exposure(comp.exposed_by(profile), comp.lines_of(profile))

    return look_through(valued_holdings, lambda vh: comp.held[vh["id"]], securities, exposure_for)


def _kind(vh: dict[str, Any], profile: EtfProfile | None) -> Kind:
    if profile is not None or vh["is_etf"]:
        return "fund"
    return "crypto" if is_crypto(vh.get("quote_type"), vh["ticker"]) else "direct"


def _index_name(kind: Kind, name: str, profile: EtfProfile | None) -> str | None:
    """Indice suivi par un fonds : celui de son profil, sinon celui que son nom désigne sans ambiguïté."""
    if kind != "fund":
        return None
    if profile is not None and profile.index_name:
        return profile.index_name
    return index_for_fund_name(profile.name if profile else name) or index_for_fund_name(name)


def _exposure_inputs(comp: _Compositions, valued_holdings: list[dict[str, Any]],
                     securities: dict[str, Security]) -> tuple[list[Holding], dict[str, dict[str, float]]]:
    """Positions du modèle d'exposition et vecteur de composition de chaque ticker (lignes du fonds exposé, ou
    société, pays et secteur d'une action en direct)."""
    holdings: list[Holding] = []
    vectors: dict[str, dict[str, float]] = {}
    for vh in valued_holdings:
        profile = comp.held[vh["id"]]
        kind = _kind(vh, profile)
        name = vh["name"] or vh["ticker"]
        security = securities.get(vh.get("isin") or vh["ticker"].upper())
        # ISIN du titre retrouvé par ticker : la clé sous laquelle la transparence range la société
        isin = vh.get("isin") or (security.isin if security else None)
        holdings.append(Holding(
            id=vh["id"], account_id=vh["account_id"], ticker=vh["ticker"], isin=isin, name=name,
            value_eur=vh["value_eur"], kind=kind, profile_id=profile.id if profile else None,
            exposure_profile_id=profile.exposure_profile_id if profile else None,
            index_name=_index_name(kind, name, profile),
        ))
        vectors[vh["ticker"]] = composition_vector(
            kind, comp.lines_of(profile), isin, vh["ticker"],
            security.country if security else None, security.sector if security else None,
        )
    return holdings, vectors


async def _market(db: Session) -> tuple[EtfProfile | None, Sequence[EtfLine]]:
    """Référence de marché et ses lignes. Elle est facultative : si on ne peut pas la lire ni la créer, le scanner
    répond quand même, avec un score neutre."""
    try:
        market = await market_reference(db)
    except Exception:  # toute panne de la référence (source, réseau, écriture) : on continue sans elle
        logger.exception("Référence de marché indisponible pour le scanner de diversification")
        db.rollback()
        return None, []
    if market is None:
        return None, []
    return market, etf_constituents.for_profiles(db, {market.id}).get(market.id, [])


async def _risk(db: Session, valued_holdings: list[dict[str, Any]],
                securities: dict[str, Security]) -> tuple[LookThrough, RiskView, EtfProfile | None]:
    """Expositions (pour nommer les chemins des sociétés), transparence, référence de marché et vue de risque."""
    comp = _compositions(db, valued_holdings)
    holdings, vectors = _exposure_inputs(comp, valued_holdings, securities)
    returns = await weekly_returns_eur(db, [h.ticker for h in holdings])
    groups = group_exposures(holdings, same_fund_rule(returns, vectors))
    label = {h.id: g.name for g in groups for h in g.holdings}
    labelled = [{**vh, "source_label": label.get(vh["id"])} for vh in valued_holdings]
    lt = _look_through(comp, labelled, securities)

    market, market_lines = await _market(db)
    view = await risk_view(db, holdings, lt, vectors, market, market_lines, returns_by_ticker=returns)
    return lt, view, market


def _risk_fields(view: RiskView, market: EtfProfile | None, accounts: list[Account]) -> dict[str, Any]:
    return {
        "exposures": exposures_payload(view.groups, {a.id: a.name for a in accounts}),
        "concentration": concentration_payload(view.groups, view.effective_bets, view.blocks,
                                               pairs_by_source(view.matrix)),
        "market": market_payload(market.name, market.ticker, view.gaps) if market else None,
        "stock_picking": view.stock_picking,
        "coverage": view.coverage,
    }


def _score_label(view: RiskView, market: EtfProfile | None) -> str:
    if market is None:
        return tr("diversity.score_no_reference")
    if not any(gap.comparable and gap.covered_pct > 0 for gap in (view.gaps or {}).values()):
        return tr("diversity.score_no_composition")
    return score_label(view.score)


async def compute_diversity(db: Session, account_id: int | None) -> dict[str, Any]:
    """Expositions réelles (sociétés, pays, secteurs), vrais doublons, corrélations, écart au marché (score et
    alertes) et vue patrimoine total."""
    holdings = repo.holdings(db, account_id)
    quotes = await market_quotes.get_market_quotes([h.ticker for h in holdings], db=db)
    market_quotes.persist_fetched_prices(db)
    valued_holdings, total_stocks_eur = await _value_holdings(db, holdings, quotes, await get_exchange_rates("EUR"))
    accounts = active_accounts(db)
    side = await _wealth_context(db, accounts)
    accounts_eur = round(await _accounts_value(db, account_id), 2)
    # Patrimoine total : actions valorisées par positions (ou repli) + épargne, liquidités et fonds euros
    total_wealth_eur = round(total_stocks_eur + side["epargne"] + side["courant"] + side["fonds_euros"] + side["other"], 2)

    securities = await _direct_securities(db, valued_holdings)  # commit éventuel avant de charger les profils
    lt, view, market = await _risk(db, valued_holdings, securities)
    companies = top_companies(lt.companies, total_stocks_eur, total_wealth_eur)
    gaps = view.gaps or {}
    countries = with_market_pct(exposure_rows(lt.countries, total_stocks_eur, total_wealth_eur), gaps.get("countries"))
    sectors = with_market_pct(exposure_rows(lt.sectors, total_stocks_eur, total_wealth_eur), gaps.get("sectors"))
    alerts = market_alerts(view.gaps, view.blocks, {g.key: g for g in view.groups}, view.stock_picking,
                           [c["name"] for c in companies if c["has_overlap"]], market_weights=view.market_weights)

    return {
        "score": view.score,
        "score_label": _score_label(view, market),
        "totals": {
            "stocks_eur": round(total_stocks_eur, 2),
            "direct_eur": round(lt.direct_value_eur, 2),
            "etf_eur": round(lt.etf_value_eur, 2),
            "epargne_eur": round(side["epargne"], 2),
            "courant_eur": round(side["courant"], 2),
            "fonds_euros_eur": round(side["fonds_euros"], 2),
            "other_eur": round(side["other"], 2),
            "wealth_eur": total_wealth_eur,
            "accounts_eur": accounts_eur,
            # Valeur des comptes non couverte par les positions : espèces, fonds euros, comptes sans position,
            # écart entre relevé et cours du jour
            "outside_positions_eur": round(accounts_eur - total_stocks_eur, 2),
            "holdings_count": len(valued_holdings),
            "etfs_count": len(lt.etfs),
        },
        "top_underlying_companies": companies[:15],
        "countries": countries,
        "sectors": sectors,
        "alerts": alerts,
        "holdings": valued_holdings,
        "etf_compositions": sorted(
            ({**c, "value_eur": round(c["value_eur"], 2)} for c in lt.compositions.values()),
            key=lambda c: c["value_eur"],
            reverse=True,
        ),
        **_risk_fields(view, market, accounts),
    }
