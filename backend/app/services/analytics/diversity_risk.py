"""Vue de risque du scanner de diversification (spec sur-exposition § 1, 3 à 6).

Séries de rendements hebdomadaires en EUR, fusion des fonds d'un même indice (tracking error ou lignes communes),
matrice de corrélation des expositions, paris indépendants, blocs corrélés, écarts à la référence de marché, stock
picking redondant et couverture des données. Les calculs sont dans `domain/exposure/` ; ce module charge les cours
et les taux (en lot) et assemble."""

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.time import today_local
from app.domain.diversity import LookThrough, normalize_company_key
from app.domain.etf_composition import EtfLine, aggregate_lines, is_equity
from app.domain.exposure.concentration import Block, correlation_blocks, effective_bets
from app.domain.exposure.correlation import Matrix, Source, correlation_matrix, pair_correlation
from app.domain.exposure.identity import ExposureGroup, Holding, group_exposures
from app.domain.exposure.market_gap import NEUTRAL_SCORE, DimensionGap, dimension_gap, market_score
from app.domain.exposure.params import (
    BLOCK_CORRELATION,
    HISTORY_WEEKS,
    MIN_HISTORY_WEEKS,
    SAME_EXPOSURE_MAX_TRACKING_ERROR,
    SAME_EXPOSURE_MIN_SIMILARITY,
)
from app.domain.exposure.stats import cosine, overlap, tracking_error, weekly_returns, weighted_returns
from app.models.etf_profile import EtfProfile
from app.services.investissement.portfolio.books import FxBook, PriceBook, ensure_history

FRIDAY = 4
LINE_PREFIX = "isin:"
COUNTRY_PREFIX = "c:"


@dataclass(frozen=True)
class RiskView:
    groups: list[ExposureGroup]
    matrix: Matrix
    effective_bets: float
    blocks: list[Block]
    # Clés `companies`, `sectors`, `countries` ; None sans référence de marché
    gaps: dict[str, DimensionGap] | None
    stock_picking: list[dict[str, Any]]
    # Poids publié de chaque exposition en direct dans la référence (majorant si absente d'un top partiel) ;
    # None sans référence. Une crypto n'a pas d'équivalent de marché.
    market_weights: dict[str, float] | None
    # `with_prices_pct` : part de la valeur avec historique de cours ; `composition_pct` : avec composition connue
    coverage: dict[str, float]
    score: float


def _fridays(first: date, end: date) -> list[date]:
    day = first + timedelta(days=(FRIDAY - first.weekday()) % 7)
    fridays = []
    while day <= end:
        fridays.append(day)
        day += timedelta(weeks=1)
    return fridays


async def weekly_returns_eur(db: Session, tickers: list[str]) -> dict[str, dict[date, float]]:
    """Rendements hebdomadaires sur `HISTORY_WEEKS`, sur des cours du vendredi convertis en EUR aux taux du jour.

    Un titre sans cours est absent. L'historique manquant est téléchargé par `ensure_history` (au plus une tentative
    par titre toutes les 6 h) ; les taux de la période sont préchargés en une requête par devise."""
    wanted = sorted(set(tickers))
    today = today_local()
    start = today - timedelta(weeks=HISTORY_WEEKS)
    book = PriceBook()
    await ensure_history(db, book, wanted, start, fetch=True)
    fx = FxBook(db)
    await fx.preload(book.currencies(), "EUR", start, today)

    out: dict[str, dict[date, float]] = {}
    for ticker in wanted:
        first = book.first_date(ticker)
        if first is None:
            continue
        series = []
        for friday in _fridays(max(first, start), today):
            found = book.price_on(ticker, friday)
            eur = await fx.convert(found[0], found[1], "EUR", friday) if found else None
            if eur is not None:
                series.append((friday, eur))
        returns = weekly_returns(series)
        if returns:
            out[ticker] = returns
    return out


def _lines_only(vector: Mapping[str, float] | None) -> dict[str, float]:
    return {k: v for k, v in (vector or {}).items() if k.startswith(LINE_PREFIX)}


def _countries_only(vector: Mapping[str, float] | None) -> dict[str, float]:
    return {k: v for k, v in (vector or {}).items() if k.startswith(COUNTRY_PREFIX)}


def same_fund_rule(
    returns: Mapping[str, Mapping[date, float]],
    vectors: Mapping[str, Mapping[str, float]],
) -> Callable[[Holding, Holding], bool]:
    """Deux fonds sont le même indice (appelée seulement si l'un des indices est inconnu, `group_exposures`) :
    tracking error ≤ 2 % si calculable ; sinon lignes communes (cosinus ≥ 0,95) **et** pays connus des deux côtés
    avec un recouvrement ≥ 0,95. Les lignes seules ne suffisent pas : les méga-caps US rendent le S&P 500 et le
    World presque colinéaires."""

    def same(a: Holding, b: Holding) -> bool:
        series_a, series_b = returns.get(a.ticker), returns.get(b.ticker)
        if series_a and series_b:
            te = tracking_error(series_a, series_b)
            if te is not None:
                return te <= SAME_EXPOSURE_MAX_TRACKING_ERROR
        vector_a, vector_b = vectors.get(a.ticker), vectors.get(b.ticker)
        lines_a, lines_b = _lines_only(vector_a), _lines_only(vector_b)
        countries_a, countries_b = _countries_only(vector_a), _countries_only(vector_b)
        if not (lines_a and lines_b and countries_a and countries_b):
            return False
        return (cosine(lines_a, lines_b) >= SAME_EXPOSURE_MIN_SIMILARITY
                and overlap(countries_a, countries_b) >= SAME_EXPOSURE_MIN_SIMILARITY)

    return same


def _weights_json(raw: str | None) -> dict[str, float]:
    try:
        return {str(k): float(v) for k, v in json.loads(raw or "{}").items()}
    except (TypeError, ValueError, AttributeError):
        return {}


def _market_companies(market: EtfProfile, lines: Sequence[EtfLine]) -> tuple[dict[str, float], dict[str, str], float | None]:
    """(poids par société, nom par société, majorant d'une société absente) : lignes entières, sinon top holdings."""
    weights: dict[str, float] = {}
    names: dict[str, str] = {}
    if lines:
        for line in lines:
            if is_equity(line) and line.weight > 0:
                key = normalize_company_key(line.ticker, line.name, line.isin)
                weights[key] = weights.get(key, 0.0) + line.weight
                names.setdefault(key, line.name)
        return weights, names, None
    try:
        top = json.loads(market.top_holdings or "[]")
        for item in top:
            key = normalize_company_key(item.get("ticker"), item["name"], item.get("isin"))
            weights[key] = weights.get(key, 0.0) + float(item.get("weight", 0.0))
            names.setdefault(key, item["name"])
    except (TypeError, ValueError, KeyError, AttributeError):
        weights, names = {}, {}
    floor = min((w for w in weights.values() if w > 0), default=None)
    return weights, names, floor


def market_gaps(lt: LookThrough, market: EtfProfile, market_lines: Sequence[EtfLine]) -> dict[str, DimensionGap]:
    """Écart du portefeuille (look-through) à la référence, par dimension ; les sociétés prennent leur nom affiché."""
    if market_lines:
        aggregates = aggregate_lines(market_lines)
        countries, sectors = aggregates["countries"], aggregates["sectors"]
    else:
        countries, sectors = _weights_json(market.countries), _weights_json(market.sectors)
    market_weights, market_names, floor = _market_companies(market, market_lines)
    mine = {key: c["direct_value_eur"] + c["indirect_value_eur"] for key, c in lt.companies.items()}
    # Sociétés : en % de toute la valeur boursière (la part que les compositions ne décrivent pas reste non décrite)
    total = lt.etf_value_eur + lt.direct_value_eur or sum(mine.values())
    mine_pct = {key: value * 100 / total for key, value in mine.items()} if total > 0 else {}
    names = market_names | {key: c["name"] for key, c in lt.companies.items()}
    companies = dimension_gap(mine_pct, market_weights, floor, renormalize=False)
    companies = replace(companies, rows=tuple(replace(r, name=names.get(r.name, r.name)) for r in companies.rows))
    return {
        "companies": companies,
        "sectors": dimension_gap(lt.sectors, sectors),
        "countries": dimension_gap(lt.countries, countries),
    }


def _market_weights(groups: Sequence[ExposureGroup], market: EtfProfile,
                    market_lines: Sequence[EtfLine]) -> dict[str, float]:
    """Poids publié de chaque exposition en direct dans la référence (0 si absente d'une composition complète, le
    plus petit poids du top si absente d'un top partiel)."""
    weights, _, floor = _market_companies(market, market_lines)
    out = {}
    for group in (g for g in groups if g.kind == "direct"):
        main = group.holdings[0]
        out[group.key] = weights.get(normalize_company_key(main.ticker, main.name, main.isin), floor or 0.0)
    return out


def _core_vector(funds: Sequence[ExposureGroup], vectors: Mapping[str, Mapping[str, float]]) -> dict[str, float]:
    total = sum(g.value_eur for g in funds)
    core: dict[str, float] = {}
    for group in funds:
        for k, v in vectors.get(group.key, {}).items():
            core[k] = core.get(k, 0.0) + v * group.value_eur / total
    return core


def stock_picking(
    groups: Sequence[ExposureGroup],
    lt: LookThrough,
    returns: Mapping[str, Mapping[date, float]],
    vectors: Mapping[str, Mapping[str, float]],
) -> list[dict[str, Any]]:
    """Par ligne en direct : part déjà détenue via les fonds et corrélation avec le cœur (les fonds, pondérés)."""
    funds = [g for g in groups if g.kind == "fund"]
    core_returns = weighted_returns({g.key: returns[g.key] for g in funds if g.key in returns},
                                    {g.key: g.value_eur for g in funds})
    core_vector = _core_vector(funds, vectors) if funds else {}
    picks = []
    for group in (g for g in groups if g.kind == "direct"):
        main = group.holdings[0]
        company = lt.companies.get(normalize_company_key(main.ticker, main.name, main.isin), {})
        indirect = float(company.get("indirect_value_eur", 0.0))
        rho, source = pair_correlation(returns.get(group.key), core_returns, vectors.get(group.key), core_vector)
        picks.append({
            "key": group.key,
            "name": group.name,
            "ticker": main.ticker,
            "value_eur": round(group.value_eur, 2),
            "indirect_value_eur": round(indirect, 2),
            "indirect_pct": round(indirect / group.value_eur * 100, 2),
            "correlation_with_core": None if rho is None else round(rho, 2),
            "source": source,
            "redundant": indirect > 0 and rho is not None and rho >= BLOCK_CORRELATION,
        })
    return picks


def _coverage(groups: Sequence[ExposureGroup], returns: Mapping[str, Mapping[date, float]],
              vectors: Mapping[str, Mapping[str, float]]) -> dict[str, float]:
    total = sum(g.value_eur for g in groups)

    def share(test: Callable[[ExposureGroup], bool]) -> float:
        return round(sum(g.value_eur for g in groups if test(g)) / total * 100, 2) if total > 0 else 0.0

    return {
        "with_prices_pct": share(lambda g: len(returns.get(g.key, {})) >= MIN_HISTORY_WEEKS),
        "composition_pct": share(lambda g: bool(vectors.get(g.key))),
    }


def pairs_by_source(matrix: Matrix) -> dict[Source, int]:
    """Nombre de paires (hors diagonale) par source de corrélation."""
    counts: dict[Source, int] = {"prices": 0, "composition": 0, "unknown": 0}
    n = len(matrix.keys)
    for i in range(n):
        for j in range(i + 1, n):
            counts[matrix.source[i][j]] += 1
    return counts


async def risk_view(
    db: Session,
    holdings: list[Holding],
    lt: LookThrough,
    vectors_by_ticker: Mapping[str, Mapping[str, float]],
    market: EtfProfile | None,
    market_lines: Sequence[EtfLine],
    returns_by_ticker: Mapping[str, Mapping[date, float]] | None = None,
) -> RiskView:
    """Expositions, corrélations, concentration, écarts au marché, stock picking et couverture d'un portefeuille.

    Une exposition fusionnée prend la série et le vecteur de son plus gros support. `returns_by_ticker` : séries
    déjà lues par l'appelant (`weekly_returns_eur`), pour ne pas relire les cours."""
    if returns_by_ticker is None:
        returns_by_ticker = await weekly_returns_eur(db, [h.ticker for h in holdings])
    groups = group_exposures(holdings, same_fund_rule(returns_by_ticker, vectors_by_ticker))
    returns = {g.key: returns_by_ticker[g.holdings[0].ticker] for g in groups if g.holdings[0].ticker in returns_by_ticker}
    vectors = {g.key: dict(vectors_by_ticker.get(g.holdings[0].ticker, {})) for g in groups}

    keys = [g.key for g in groups]
    weights = [g.value_eur for g in groups]
    matrix = correlation_matrix(keys, returns, vectors)
    gaps = market_gaps(lt, market, market_lines) if market is not None else None
    return RiskView(
        groups=groups,
        matrix=matrix,
        effective_bets=effective_bets(weights, matrix.rho),
        blocks=correlation_blocks(keys, weights, matrix.rho),
        gaps=gaps,
        stock_picking=stock_picking(groups, lt, returns, vectors),
        market_weights=_market_weights(groups, market, market_lines) if market is not None else None,
        coverage=_coverage(groups, returns, vectors),
        score=market_score(list(gaps.values())) if gaps is not None else NEUTRAL_SCORE,
    )
