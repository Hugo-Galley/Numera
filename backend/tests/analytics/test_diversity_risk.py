"""Vue de risque du scanner : séries en EUR, fusion par tracking error, corrélations, stock picking (spec § 1, 3, 6).

Sans réseau : cours dans `security_prices`, taux dans `historical_exchange_rates`, sur toute la fenêtre de 2 ans."""
import asyncio
import math
from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.time import today_local
from app.domain.diversity import LookThrough, normalize_company_key
from app.domain.etf_composition import EtfConstituentRow
from app.domain.exposure.identity import Holding, Kind
from app.domain.exposure.params import HISTORY_WEEKS
from app.models.etf_profile import EtfProfile
from app.models.exchange_rate import HistoricalExchangeRate
from app.models.security_price import SecurityPrice
from app.services.analytics.diversity_risk import RiskView, pairs_by_source, risk_view, weekly_returns_eur

WEEKS = HISTORY_WEEKS + 2
APPLE_ISIN = "US0378331005"


def _fridays(weeks: int = WEEKS) -> list[date]:
    today = today_local()
    last = today - timedelta(days=(today.weekday() - 4) % 7)
    return [last - timedelta(weeks=weeks - 1 - i) for i in range(weeks)]


def _market(i: int) -> float:
    """Rendement hebdomadaire d'un indice large (écart-type ≈ 2,1 %)."""
    return 0.03 * math.sin(1.7 * i)


def _store(db: Session, ticker: str, returns: list[float], currency: str = "EUR") -> None:
    close = 100.0
    for i, friday in enumerate(_fridays()):
        close *= 1 + returns[i]
        db.add(SecurityPrice(ticker=ticker, date=friday, close=close, currency=currency, source="test"))
    db.commit()


def _alternating(amplitude: float, base=_market) -> list[float]:
    return [base(i) + amplitude * (1 if i % 2 else -1) for i in range(WEEKS)]


def _holding(id: int, ticker: str, value: float, kind: Kind = "fund", *, isin: str | None = None,
             profile_id: int | None = None) -> Holding:
    return Holding(id=id, account_id=1, ticker=ticker, isin=isin, name=ticker, value_eur=value, kind=kind,
                   profile_id=profile_id, exposure_profile_id=None, index_name=None)


def _view(db: Session, holdings: list[Holding], vectors: dict[str, dict[str, float]] | None = None,
          lt: LookThrough | None = None, market: EtfProfile | None = None) -> RiskView:
    return asyncio.run(risk_view(db, holdings, lt or LookThrough(), vectors or {}, market, []))


def test_same_index_funds_merge_by_tracking_error(db_session: Session):
    _store(db_session, "WLD1", [_market(i) for i in range(WEEKS)])
    _store(db_session, "WLD2", _alternating(0.0005))

    view = _view(db_session, [_holding(1, "WLD1", 5000, profile_id=1), _holding(2, "WLD2", 3000, profile_id=2)])

    assert len(view.groups) == 1
    assert view.groups[0].value_eur == 8000
    assert view.effective_bets == 1.0


def test_sp500_and_world_not_merged_but_same_block(db_session: Session):
    _store(db_session, "WLD", [_market(i) for i in range(WEEKS)])
    _store(db_session, "SP5", _alternating(0.0055))

    view = _view(db_session, [_holding(1, "WLD", 5000, profile_id=1), _holding(2, "SP5", 3000, profile_id=2)])

    assert len(view.groups) == 2
    assert view.matrix.source[0][1] == "prices"
    assert view.matrix.rho[0][1] == pytest.approx(0.97, abs=0.02)
    assert len(view.blocks) == 1
    assert set(view.blocks[0].keys) == {"exp:WLD", "exp:SP5"}


def test_usd_quotes_converted_before_returns(db_session: Session):
    fridays = _fridays()
    _store(db_session, "AAPL", [0.01] * WEEKS, currency="USD")
    usd_per_eur = {friday: 1.0 + 0.01 * (i % 5) for i, friday in enumerate(fridays)}
    db_session.add_all(HistoricalExchangeRate(date=d, currency="USD", rate=r) for d, r in usd_per_eur.items())
    db_session.commit()

    returns = asyncio.run(weekly_returns_eur(db_session, ["AAPL"]))["AAPL"]

    week, previous = fridays[-1], fridays[-2]
    expected = (1.01 / usd_per_eur[week]) / (1 / usd_per_eur[previous]) - 1
    assert returns[week] == pytest.approx(expected)
    assert len(returns) >= HISTORY_WEEKS - 1


def test_fund_without_history_uses_composition(db_session: Session):
    _store(db_session, "WLD", [_market(i) for i in range(WEEKS)])
    vectors = {
        "WLD": {"isin:A": 5.0, "isin:B": 4.0, "c:USA": 70.0, "c:JPN": 6.0},
        "0P0000XYZ": {"isin:A": 3.0, "isin:C": 5.0, "c:USA": 50.0, "c:FRA": 30.0},
    }

    view = _view(db_session, [_holding(1, "WLD", 6000, profile_id=1), _holding(2, "0P0000XYZ", 2000, profile_id=2)],
                 vectors)

    assert len(view.groups) == 2
    assert view.matrix.source[0][1] == "composition"
    assert pairs_by_source(view.matrix) == {"prices": 0, "composition": 1, "unknown": 0}
    assert view.matrix.rho[0][1] is not None
    assert view.coverage["with_prices_pct"] == pytest.approx(75.0)
    assert view.coverage["composition_pct"] == pytest.approx(100.0)


def test_redundant_pick(db_session: Session):
    _store(db_session, "WLD", [_market(i) for i in range(WEEKS)])
    _store(db_session, "AAPL", _alternating(0.0105))
    lt = LookThrough()
    lt.company(normalize_company_key("AAPL", "Apple", APPLE_ISIN), "Apple", "AAPL")["indirect_value_eur"] = 295.0

    view = _view(db_session, [_holding(1, "WLD", 6000, profile_id=1),
                              _holding(2, "AAPL", 356, "direct", isin=APPLE_ISIN)], lt=lt)

    assert len(view.stock_picking) == 1
    pick = view.stock_picking[0]
    assert pick["name"] == "AAPL"
    assert pick["indirect_value_eur"] == pytest.approx(295.0)
    assert pick["source"] == "prices"
    assert pick["correlation_with_core"] == pytest.approx(0.9, abs=0.03)
    assert pick["redundant"] is True


def test_without_market_score_is_neutral(db_session: Session):
    view = _view(db_session, [_holding(1, "BTC-USD", 500, "crypto")])

    assert view.gaps is None
    assert view.score == 50.0
    assert view.blocks == []
    assert view.effective_bets == 1.0


def test_market_gaps_by_dimension(db_session: Session):
    lt = LookThrough()
    lt.countries = {"USA": 900.0, "Non renseigné": 100.0}
    lt.sectors = {"Technologie": 1000.0}
    lt.company(normalize_company_key("AAPL", "Apple", APPLE_ISIN), "Apple", "AAPL")["direct_value_eur"] = 1000.0
    market = EtfProfile(name="ACWI", ticker="SSAC.L", countries='{"USA": 60, "JPN": 40}',
                        sectors='{"Technologie": 25, "Finance": 75}',
                        top_holdings=f'[{{"name": "APPLE INC", "isin": "{APPLE_ISIN}", "weight": 4.0}},'
                                     '{"name": "Microsoft", "ticker": "MSFT", "weight": 3.5}]')

    view = asyncio.run(risk_view(db_session, [_holding(1, "AAPL", 1000, "direct", isin=APPLE_ISIN)], lt, {},
                                 market, []))

    assert view.gaps is not None
    assert set(view.gaps) == {"companies", "sectors", "countries"}
    assert view.gaps["countries"].active_share_pct == pytest.approx(40.0)
    assert view.gaps["sectors"].active_share_pct == pytest.approx(75.0)
    apple = next(r for r in view.gaps["companies"].rows if r.name == "Apple")
    assert apple.market_pct == pytest.approx(4.0 / 7.5 * 100)
    assert view.score == pytest.approx(round(100 - (40 + 75 + view.gaps["companies"].active_share_pct) / 3, 1))


def test_market_lines_compare_whole_composition(db_session: Session):
    lt = LookThrough()
    lt.countries = {"USA": 1000.0}
    lt.sectors = {"Technologie": 1000.0}
    lt.company("TICKER:ZZZ", "Zeta", "ZZZ")["direct_value_eur"] = 1000.0
    lines = [EtfConstituentRow(APPLE_ISIN, "AAPL", "Apple", 50.0, "USA", "Technologie", "Actions"),
             EtfConstituentRow(None, "MSFT", "Microsoft", 50.0, "USA", "Technologie", "Actions")]
    market = EtfProfile(name="ACWI", ticker="SSAC.L", countries="{}", sectors="{}", top_holdings="[]")

    view = asyncio.run(risk_view(db_session, [_holding(1, "ZZZ", 1000, "direct")], lt, {}, market, lines))

    assert view.gaps is not None
    assert view.gaps["countries"].active_share_pct == pytest.approx(0.0)
    zeta = next(r for r in view.gaps["companies"].rows if r.name == "Zeta")
    assert zeta.market_pct == 0.0
    assert zeta.market_pct_is_upper_bound is False
