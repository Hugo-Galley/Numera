"""Actualisation des compositions d'ETF : chaîne de sources, synthétiques, agrégats, référentiel des titres.

Les émetteurs sont les vrais modules, servis par les jeux de test réels réduits (`httpx.MockTransport`)."""
import asyncio
import json
from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy.orm import Session

from app.core.circuit_breaker import reset_all
from app.core.time import utcnow_naive
from app.domain import etf_composition as composition_rules
from app.integrations import yahoo_finance
from app.integrations.etf_providers.amundi import Amundi
from app.integrations.etf_providers.base import Constituent
from app.integrations.etf_providers.ishares import IShares
from app.integrations.etf_providers.justetf import JustEtf
from app.models.account import Account
from app.models.etf_constituent import EtfConstituent
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding
from app.models.security import Security
from app.repositories.investissement import etf_constituents
from app.schemas.etf_profile import EtfProfileUpdate
from app.services.investissement import etf_composition
from app.services.investissement.etf_profiles import (
    auto_decompose_and_create_profile,
    refresh_held_etf_profiles,
    update_profile,
)
from tests.investissement.etf_provider_helpers import fixture_bytes, mock_factory

WORLD = "IE00B4L5Y983"
CW8 = "LU1681043599"
AMUNDI_WORLD = "IE000BI8OT95"
APPLE = "US0378331005"


@pytest.fixture(autouse=True)
def reduced_fixtures(monkeypatch):
    """Les jeux de test ne gardent qu'une partie des lignes (≈ 37 % du fonds) : seuil abaissé pour eux seuls."""
    monkeypatch.setattr(composition_rules, "MIN_TOTAL_WEIGHT", 30.0)


@pytest.fixture(autouse=True)
def yahoo(monkeypatch):
    """Yahoo, dernier recours : ne connaît rien, sauf si le test remplit `answers`."""
    state = {"calls": [], "answers": {}, "down": False}

    async def fake(symbol):
        state["calls"].append(symbol)
        if state["down"]:
            raise yahoo_finance.YahooUnavailable("hors ligne")
        return state["answers"].get(symbol)

    monkeypatch.setattr(yahoo_finance, "fetch_composition", fake)
    return state


def _ishares_handler(request: httpx.Request) -> httpx.Response:
    if "product-screener" in str(request.url):
        return httpx.Response(200, content=fixture_bytes("ishares_catalog.json"))
    if request.url.params["portfolioId"] == "251882":
        return httpx.Response(200, content=fixture_bytes("ishares_holdings_251882.json"))
    return httpx.Response(404)


def _amundi_handler(request: httpx.Request) -> httpx.Response:
    isin = json.loads(request.content)["productIds"][0]
    if isin in (AMUNDI_WORLD, CW8):
        return httpx.Response(200, content=fixture_bytes(f"amundi_{isin}.json"))
    return httpx.Response(200, json={"products": []})


def _justetf_handler(request: httpx.Request) -> httpx.Response:
    if request.url.params["isin"] == AMUNDI_WORLD:
        return httpx.Response(200, content=fixture_bytes("justetf_IE000BI8OT95.html"))
    return httpx.Response(200, text="<html></html>")


def _providers(ishares=_ishares_handler, amundi=_amundi_handler, justetf=_justetf_handler, seen=None):
    return [
        IShares(client_factory=mock_factory(ishares, seen)),
        Amundi(client_factory=mock_factory(amundi, seen)),
        JustEtf(client_factory=mock_factory(justetf, seen)),
    ]


def _profile(db: Session, isin: str | None = WORLD, name: str = "Fonds", ticker: str = "FND.PA", **fields) -> EtfProfile:
    profile = EtfProfile(name=name, ticker=ticker, isin=isin, aliases=json.dumps([ticker]), **fields)
    db.add(profile)
    db.commit()
    return profile


def _hold(db: Session, profile: EtfProfile) -> None:
    account = db.query(Account).first()
    if not account:
        account = Account(name="PEA", type="investissement", currency="EUR", active=True)
        db.add(account)
        db.commit()
    db.add(PortfolioHolding(account_id=account.id, ticker=profile.ticker, asset_name=profile.name,
                            quantity=1.0, buy_price_avg=10.0, currency="EUR", etf_profile_id=profile.id))
    db.commit()


def _refresh(db: Session, profile: EtfProfile, providers=None) -> list[str]:
    return asyncio.run(etf_composition.refresh(db, profile, _providers() if providers is None else providers))


def _lines(db: Session, profile: EtfProfile) -> list[EtfConstituent]:
    return db.query(EtfConstituent).filter(EtfConstituent.profile_id == profile.id).all()


def test_refresh_stores_all_lines(db_session: Session):
    profile = _profile(db_session)
    updated = _refresh(db_session, profile)

    assert sorted(updated) == ["countries", "sectors", "top_holdings"]
    db_session.expire_all()
    lines = _lines(db_session, profile)
    assert len(lines) == 28
    assert (profile.provider, profile.provider_ref, profile.replication, profile.index_name) == (
        "ishares", "251882", "physical", "MSCI World")
    assert profile.composition_as_of == date(2026, 11, 25)
    assert profile.composition_refreshed_at is not None
    assert profile.lines_count == 28
    equities = [x for x in lines if x.asset_class == "Equity"]
    assert profile.coverage_pct == pytest.approx(sum(x.weight for x in equities), abs=0.01)
    countries = json.loads(profile.countries)
    assert countries["USA"] == pytest.approx(sum(x.weight for x in equities if x.country == "USA"), abs=0.001)
    top = json.loads(profile.top_holdings)
    assert len(top) == 10
    assert (top[0]["isin"], top[0]["weight"]) == (APPLE, pytest.approx(6.13244))
    assert "APPLE" in top[0]["name"].upper()
    assert json.loads(profile.composition_sources) == {
        "countries": "ishares", "sectors": "ishares", "top_holdings": "ishares"}


def test_refreshing_twice_replaces_lines(db_session: Session):
    profile = _profile(db_session)
    _refresh(db_session, profile)
    _refresh(db_session, profile)
    assert len(_lines(db_session, profile)) == 28


def test_lines_are_read_by_profile_without_orm_objects(db_session: Session):
    profile = _profile(db_session)
    _refresh(db_session, profile)
    by_profile = etf_constituents.for_profiles(db_session, [profile.id, 999])
    assert list(by_profile) == [profile.id]
    row = max(by_profile[profile.id], key=lambda r: r.weight)
    assert (row.isin, row.country, row.sector, row.asset_class) == (APPLE, "USA", "Technologie", "Equity")
    assert not isinstance(row, EtfConstituent)
    assert etf_constituents.for_profiles(db_session, []) == {}


def test_synthetic_uses_index_reference(db_session: Session):
    synthetic = _profile(db_session, isin=CW8, name="CW8", ticker="CW8.PA",
                         countries=json.dumps({"USA": 71.0}), sectors=json.dumps({"Finance": 15.0}),
                         composition_sources=json.dumps({"countries": "preset", "sectors": "preset"}))
    _refresh(db_session, synthetic)

    db_session.expire_all()
    reference = db_session.query(EtfProfile).filter(EtfProfile.isin == WORLD).one()
    assert (reference.name, reference.is_system, reference.provider) == ("MSCI World", False, "ishares")
    assert (synthetic.replication, synthetic.index_name, synthetic.exposure_profile_id) == (
        "synthetic", "MSCI World", reference.id)
    assert (synthetic.provider, synthetic.lines_count) == ("amundi", 0)
    assert synthetic.composition_as_of == reference.composition_as_of
    assert synthetic.coverage_pct == reference.coverage_pct
    assert (synthetic.countries, synthetic.sectors, synthetic.top_holdings) == ("{}", "{}", "[]")
    assert json.loads(synthetic.composition_sources) == {}
    assert _lines(db_session, synthetic) == []
    assert len(_lines(db_session, reference)) == 28


def test_synthetic_reuses_a_fresh_reference(db_session: Session):
    reference = _profile(db_session, isin=WORLD, name="Mon World", ticker="SWDA.L")
    _refresh(db_session, reference)
    synthetic = _profile(db_session, isin=CW8, name="CW8", ticker="CW8.PA")
    seen: list[httpx.Request] = []
    _refresh(db_session, synthetic, _providers(seen=seen))
    assert synthetic.exposure_profile_id == reference.id
    assert not [r for r in seen if "get-product-data" in str(r.url)]
    assert db_session.query(EtfProfile).count() == 2


def test_synthetic_is_linked_even_if_its_reference_cannot_be_read(db_session: Session):
    synthetic = _profile(db_session, isin=CW8, name="CW8", ticker="CW8.PA")
    _refresh(db_session, synthetic, _providers(ishares=lambda r: httpx.Response(500)))
    reference = db_session.query(EtfProfile).filter(EtfProfile.isin == WORLD).one()
    assert synthetic.exposure_profile_id == reference.id
    assert reference.composition_refreshed_at is None
    assert synthetic.coverage_pct == 0


def test_synthetic_without_known_index_uses_no_basket(db_session: Session, yahoo):
    def unknown_index(request):
        payload = json.loads(fixture_bytes(f"amundi_{CW8}.json"))
        payload["products"][0]["characteristics"]["SHARE_MARKETING_NAME"] = "Amundi MSCI World Banks Swap UCITS ETF"
        return httpx.Response(200, json=payload) if json.loads(request.content)["productIds"][0] == CW8 \
            else httpx.Response(200, json={"products": []})

    yahoo["answers"]["BNK.PA"] = {"sectors": {"Finance": 100.0}}
    profile = _profile(db_session, isin=CW8, ticker="BNK.PA", countries=json.dumps({"USA": 100.0}),
                       composition_sources=json.dumps({"countries": "preset"}))
    _refresh(db_session, profile, _providers(amundi=unknown_index))

    db_session.expire_all()
    assert (profile.replication, profile.exposure_profile_id, profile.coverage_pct, profile.lines_count) == (
        "synthetic", None, 0, 0)
    assert (profile.countries, profile.sectors, profile.top_holdings) == ("{}", "{}", "[]")
    assert _lines(db_session, profile) == []
    assert db_session.query(EtfProfile).count() == 1
    assert yahoo["calls"] == []


@pytest.mark.parametrize("answer", [
    httpx.Response(200, text="<html>maintenance</html>"),
    httpx.Response(200, json={"componentsByNameMap": {}}),
    "half",
])
def test_refresh_keeps_previous_composition_on_empty_provider_answer(db_session: Session, yahoo, answer, monkeypatch):
    profile = _profile(db_session)
    _refresh(db_session, profile)
    before = (profile.countries, profile.sectors, profile.top_holdings, profile.composition_refreshed_at,
              profile.composition_as_of, profile.provider, profile.coverage_pct)
    if answer == "half":  # somme des poids sous le seuil
        monkeypatch.setattr(composition_rules, "MIN_TOTAL_WEIGHT", 50.0)
        handler = _ishares_handler
    else:
        def handler(request):
            return _ishares_handler(request) if "product-screener" in str(request.url) else answer
    yahoo["answers"][profile.ticker] = {"sectors": {"Finance": 100.0}}
    reset_all()

    with pytest.raises(etf_composition.CompositionUnavailable):
        _refresh(db_session, profile, _providers(ishares=handler))

    db_session.expire_all()
    assert (profile.countries, profile.sectors, profile.top_holdings, profile.composition_refreshed_at,
            profile.composition_as_of, profile.provider, profile.coverage_pct) == before
    assert len(_lines(db_session, profile)) == 28


def test_lines_are_never_replaced_by_aggregates(db_session: Session, yahoo):
    """Le fonds disparaît des catalogues : le dernier détail reste, Yahoo et justETF ne le remplacent pas."""
    profile = _profile(db_session)
    _refresh(db_session, profile)
    sectors = profile.sectors
    yahoo["answers"][profile.ticker] = {"sectors": {"Finance": 100.0}}
    with pytest.raises(etf_composition.CompositionUnavailable):
        _refresh(db_session, profile, _providers(ishares=lambda r: httpx.Response(200, json={})))
    assert profile.sectors == sectors


def test_justetf_fallback_stores_aggregates_and_is_not_preferred_afterwards(db_session: Session):
    profile = _profile(db_session, isin=AMUNDI_WORLD)
    _refresh(db_session, profile, _providers(amundi=lambda r: httpx.Response(200, json={"products": []})))
    assert (profile.provider, profile.lines_count) == ("justetf", 0)
    assert json.loads(profile.countries)["USA"] == pytest.approx(71.05)
    assert profile.composition_as_of == utcnow_naive().date()
    assert 80 < profile.coverage_pct <= 100

    _refresh(db_session, profile)  # l'émetteur répond de nouveau : il reprend la main

    assert (profile.provider, profile.lines_count) == ("amundi", 25)


def test_remembered_issuer_is_asked_first(db_session: Session):
    profile = _profile(db_session, isin=AMUNDI_WORLD)
    _refresh(db_session, profile)
    seen: list[httpx.Request] = []
    _refresh(db_session, profile, _providers(seen=seen))
    assert {r.url.host for r in seen} == {"www.amundietf.fr"}


def test_justetf_swap_fund_is_treated_as_synthetic(db_session: Session):
    """justETF ne dit pas le mode de réplication : un nom « Swap » suffit à écarter le panier détenu."""
    def swap_page(request):
        if request.url.params["isin"] != AMUNDI_WORLD:
            return httpx.Response(200, text="<html></html>")
        page = fixture_bytes("justetf_IE000BI8OT95.html").decode()
        return httpx.Response(200, text=page.replace("Amundi Core MSCI World UCITS ETF Acc", "Xtrackers S&P 500 Swap UCITS ETF"))

    profile = _profile(db_session, isin=AMUNDI_WORLD)
    _refresh(db_session, profile, _providers(amundi=lambda r: httpx.Response(200, json={"products": []}),
                                             justetf=swap_page))
    assert (profile.replication, profile.index_name) == ("synthetic", "S&P 500")
    assert profile.countries == "{}"
    assert db_session.get(EtfProfile, profile.exposure_profile_id).isin == "IE00B5BMR087"


def test_known_synthetic_never_gets_a_fallback_basket(db_session: Session, yahoo):
    profile = _profile(db_session, isin=CW8, ticker="CW8.PA")
    _refresh(db_session, profile)
    reference_id = profile.exposure_profile_id
    yahoo["answers"]["CW8.PA"] = {"sectors": {"Finance": 100.0}}
    with pytest.raises(etf_composition.CompositionUnavailable):
        _refresh(db_session, profile, _providers(amundi=lambda r: httpx.Response(500)))
    assert (profile.sectors, profile.exposure_profile_id) == ("{}", reference_id)


def test_fallback_source_never_declares_a_known_fund_synthetic_while_its_issuer_is_down(db_session: Session):
    profile = _profile(db_session)
    _refresh(db_session, profile)

    def says_synthetic(request):
        return httpx.Response(200, text=(
            '<div data-testid="etf-profile-header_replication-value">Synthétique</div>'
            '<tr data-testid="etf-holdings_countries_row"></tr>'))

    with pytest.raises(etf_composition.CompositionUnavailable):
        _refresh(db_session, profile, _providers(ishares=lambda r: httpx.Response(500), justetf=says_synthetic))
    assert (profile.replication, profile.lines_count, len(_lines(db_session, profile))) == ("physical", 28, 28)


def test_profile_without_isin_uses_yahoo_only(db_session: Session, yahoo):
    yahoo["answers"]["WLD.PA"] = {"sectors": {"Technologie": 60.0}, "top_holdings": []}
    profile = _profile(db_session, isin=None, ticker="WLD.PA")
    seen: list[httpx.Request] = []
    assert _refresh(db_session, profile, _providers(seen=seen)) == ["sectors"]
    assert seen == []
    assert (profile.provider, profile.coverage_pct, profile.lines_count) == ("yahoo", 60.0, 0)
    assert profile.composition_as_of == utcnow_naive().date()


def test_nothing_published_is_remembered(db_session: Session):
    profile = _profile(db_session, isin="FR0000000000")
    assert _refresh(db_session, profile) == []
    assert profile.composition_refreshed_at is not None
    assert profile.provider is None


def test_nothing_obtained_while_a_source_is_down_is_retried(db_session: Session, yahoo):
    yahoo["down"] = True
    profile = _profile(db_session, isin=None)
    with pytest.raises(etf_composition.CompositionUnavailable):
        _refresh(db_session, profile)
    assert profile.composition_refreshed_at is None


def test_refresh_never_overwrites_manual_fields(db_session: Session):
    profile = _profile(db_session, countries=json.dumps({"FRA": 100.0}),
                       composition_sources=json.dumps({"countries": "manual"}))
    assert sorted(_refresh(db_session, profile)) == ["sectors", "top_holdings"]
    db_session.expire_all()
    assert json.loads(profile.countries) == {"FRA": 100.0}
    assert json.loads(profile.composition_sources)["countries"] == "manual"
    assert profile.isin == WORLD


def test_synthetic_keeps_manual_fields(db_session: Session):
    profile = _profile(db_session, isin=CW8, countries=json.dumps({"FRA": 100.0}),
                       composition_sources=json.dumps({"countries": "manual"}))
    _refresh(db_session, profile)
    assert json.loads(profile.countries) == {"FRA": 100.0}
    assert json.loads(profile.composition_sources) == {"countries": "manual"}


def test_changing_the_isin_forgets_the_previous_composition(db_session: Session):
    profile = _profile(db_session)
    _refresh(db_session, profile)
    update_profile(db_session, profile.id, EtfProfileUpdate(isin=CW8))
    assert (profile.provider, profile.provider_ref, profile.replication, profile.lines_count,
            profile.coverage_pct, profile.composition_as_of, profile.composition_refreshed_at) == (
        None, None, "unknown", 0, None, None, None)
    assert _lines(db_session, profile) == []


def test_deleting_a_profile_deletes_its_lines(db_session: Session):
    profile = _profile(db_session)
    _refresh(db_session, profile)
    db_session.delete(profile)
    db_session.commit()
    assert db_session.query(EtfConstituent).count() == 0


def test_refresh_feeds_securities(db_session: Session):
    _refresh(db_session, _profile(db_session))
    apple = db_session.get(Security, APPLE)
    assert (apple.ticker, apple.country, apple.sector, apple.source, apple.exchange) == (
        "AAPL", "USA", "Technologie", "ishares", "NASDAQ")
    equities = db_session.query(EtfConstituent).filter(
        EtfConstituent.asset_class == "Equity", EtfConstituent.isin.isnot(None)).count()
    assert db_session.query(Security).count() == equities  # ni liquidités ni contrats à terme


def test_line_without_ticker_keeps_the_known_ticker(db_session: Session):
    db_session.add(Security(isin=APPLE, ticker="AAPL", exchange="NASDAQ", name="Apple", source="ishares"))
    db_session.commit()
    line = Constituent(isin=APPLE, ticker=None, name="APPLE INC", weight=100.0, country="USA",
                       sector="Technologie", asset_class="Equity", exchange=None)
    etf_composition.remember_securities(db_session, [line], "spdr")
    db_session.commit()
    apple = db_session.get(Security, APPLE)
    db_session.refresh(apple)
    assert (apple.ticker, apple.exchange, apple.source) == ("AAPL", "NASDAQ", "spdr")


def test_refresh_query_count_does_not_grow_with_lines(db_session: Session, measure_queries):
    def count_for(size: int) -> int:
        def many_lines(request):
            if "product-screener" in str(request.url):
                return _ishares_handler(request)
            payload = json.loads(fixture_bytes("ishares_holdings_251882.json"))
            points = payload["componentsByNameMap"]["holdings"]["containersByNameMap"]["all"]["dataPointsByNameMap"]
            rows = len(points["issueName"]["value"])
            for name, point in points.items():
                if isinstance(point.get("value"), list) and len(point["value"]) == rows:
                    column = [point["value"][0]] * size
                    if name == "isin":
                        column = [f"XX{i:010d}" for i in range(size)]
                    if name == "holdingPercent":
                        column = [99.0 / size] * size
                    point["value"] = column
            return httpx.Response(200, json=payload)

        profile = _profile(db_session, name=f"P{size}", ticker=f"P{size}")
        provider = _providers(ishares=many_lines)
        _, queries = measure_queries(lambda: _refresh(db_session, profile, provider))
        assert len(_lines(db_session, profile)) == size
        return queries

    small, large = count_for(50), count_for(3000)
    assert large == small
    assert large <= 15


def test_daily_interval(db_session: Session):
    profile = _profile(db_session)
    _hold(db_session, profile)

    def run(hours: float) -> int:
        profile.composition_refreshed_at = utcnow_naive() - timedelta(hours=hours)
        db_session.commit()
        return asyncio.run(refresh_held_etf_profiles(db_session, providers=_providers()))

    assert run(23) == 0
    assert run(25) == 1


def test_refresh_held_includes_exposure_profiles(db_session: Session):
    synthetic = _profile(db_session, isin=CW8, name="CW8", ticker="CW8.PA")
    _hold(db_session, synthetic)
    assert asyncio.run(refresh_held_etf_profiles(db_session, providers=_providers())) == 1
    reference = db_session.get(EtfProfile, synthetic.exposure_profile_id)
    first = reference.composition_refreshed_at

    # La référence vieillit seule : elle est relue même si le synthétique est à jour
    reference.composition_refreshed_at = utcnow_naive() - timedelta(days=2)
    db_session.commit()
    assert asyncio.run(refresh_held_etf_profiles(db_session, providers=_providers())) == 1
    db_session.refresh(reference)
    assert reference.composition_refreshed_at > first

    seen: list[httpx.Request] = []
    assert asyncio.run(refresh_held_etf_profiles(db_session, force=True, providers=_providers(seen=seen))) == 2
    assert len([r for r in seen if "get-product-data" in str(r.url)]) == 1


def test_one_provider_down_does_not_stop_others(db_session: Session):
    broken = _profile(db_session, isin=WORLD, name="A iShares", ticker="A.L")
    other = _profile(db_session, isin="IE00B5BMR087", name="B iShares", ticker="B.L")
    amundi = _profile(db_session, isin=AMUNDI_WORLD, name="C Amundi", ticker="C.PA")
    for profile in (broken, other, amundi):
        _hold(db_session, profile)
    seen: list[httpx.Request] = []

    count = asyncio.run(refresh_held_etf_profiles(
        db_session, providers=_providers(ishares=lambda r: httpx.Response(500), seen=seen)))

    assert count == 1
    assert amundi.provider == "amundi"
    assert len([r for r in seen if "ishares" in r.url.host]) == 1  # sauté pour le reste du passage
    assert broken.composition_refreshed_at is None


def test_auto_decompose_with_isin_reads_the_issuer(db_session: Session, monkeypatch):
    monkeypatch.setattr(etf_composition, "PROVIDERS", _providers())
    profile = asyncio.run(auto_decompose_and_create_profile(db_session, symbol="swda.l", isin=WORLD))
    assert (profile.name, profile.provider, profile.lines_count) == ("iShares Core MSCI World UCITS ETF", "ishares", 28)


def test_auto_decompose_keeps_the_profile_when_sources_are_down(db_session: Session, yahoo):
    yahoo["down"] = True
    profile = asyncio.run(auto_decompose_and_create_profile(db_session, symbol="zzz.pa", name="Mon fonds"))
    assert (profile.name, profile.ticker, profile.countries) == ("Mon fonds", "ZZZ.PA", "{}")


GOLD = "FR0013416716"


def _amundi_with_empty_gold(request: httpx.Request) -> httpx.Response:
    """Un ETC or : Amundi publie sa fiche, mais aucune ligne de composition."""
    body = json.loads(request.content)
    if body["productIds"][0] != GOLD:
        return _amundi_handler(request)
    payload = json.loads(fixture_bytes(f"amundi_{AMUNDI_WORLD}.json"))
    product = payload["products"][0]
    product["productId"] = GOLD
    product["characteristics"]["SHARE_MARKETING_NAME"] = "Amundi Physical Gold ETC"
    product["composition"] = {"compositionData": []}
    return httpx.Response(200, json=payload)


def test_fund_without_lines_does_not_put_its_issuer_down(db_session: Session):
    gold = _profile(db_session, isin=GOLD, name="AAA Gold", ticker="GOLD.PA")
    world = _profile(db_session, isin=AMUNDI_WORLD, name="ZZZ Amundi World", ticker="MWRD.PA")
    for profile in (gold, world):
        _hold(db_session, profile)

    asyncio.run(refresh_held_etf_profiles(db_session, providers=_providers(amundi=_amundi_with_empty_gold)))

    assert (world.provider, world.lines_count) == ("amundi", 25)
    assert gold.composition_refreshed_at is not None  # tenté : pas relu avant l'intervalle
    assert gold.lines_count in (0, None)


def test_fund_missing_at_its_issuer_does_not_put_the_issuer_down(db_session: Session):
    """Une page 404 pour un fonds (portfolioId inconnu) ne fait pas sauter les autres fonds de l'émetteur."""
    missing = _profile(db_session, isin="IE00B5BMR087", name="A iShares", ticker="A.L")
    world = _profile(db_session, isin=WORLD, name="B iShares", ticker="B.L")
    for profile in (missing, world):
        _hold(db_session, profile)

    asyncio.run(refresh_held_etf_profiles(db_session, providers=_providers()))

    assert (world.provider, world.lines_count) == ("ishares", 28)
    assert missing.composition_refreshed_at is not None
