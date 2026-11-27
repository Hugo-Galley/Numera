"""Fiche d'un ETF : identité, pays, secteurs, toutes les lignes et valeur détenue."""
import json

import pytest

from app.domain.etf_composition import EtfConstituentRow
from app.models.account import Account
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding
from app.repositories.investissement import etf_constituents
from app.services.investissement.market import quotes as market_quotes


@pytest.fixture(autouse=True)
def quotes(monkeypatch):
    """Cours fixes : 100 € pour tout ticker, sauf `NOQUOTE.PA` (aucun cours : repli sur le PRU)."""
    async def fake(symbols, db=None):
        return {s.upper(): {"price_eur": 0.0 if s.upper() == "NOQUOTE.PA" else 100.0} for s in symbols}

    monkeypatch.setattr(market_quotes, "get_market_quotes", fake)


def _profile(db, name="World", **kw):
    values = {"ticker": f"{name[:3].upper()}.PA", "aliases": "[]", **kw}
    profile = EtfProfile(name=name, **values)
    db.add(profile)
    db.commit()
    return profile


def _line(name, weight, country="USA", sector="Technologie", ticker=None, isin=None, asset_class="Equity"):
    return EtfConstituentRow(isin, ticker, name, weight, country, sector, asset_class)


def _with_lines(db, profile, lines):
    etf_constituents.replace(db, profile.id, lines)
    profile.lines_count = len(lines)
    profile.coverage_pct = sum(x.weight for x in lines)
    db.commit()


def test_sheet_of_physical_etf_lists_all_lines_sorted_by_weight(client, db_session):
    profile = _profile(db_session, provider="ishares", replication="physical", isin="IE00B4L5Y983",
                       countries=json.dumps({"JPN": 99.0}), composition_sources=json.dumps({"countries": "ishares"}))
    _with_lines(db_session, profile, [
        _line("Nestlé", 2.0, "CHE", "Consommation de base"),
        _line("Apple", 5.0, ticker="AAPL", isin="US0378331005"),
        _line("Microsoft", 3.0),
    ])

    resp = client.get(f"/etf-profiles/{profile.id}/constituents")

    assert resp.status_code == 200
    sheet = resp.json()
    assert [(x["name"], x["weight"]) for x in sheet["lines"]] == [("Apple", 5.0), ("Microsoft", 3.0), ("Nestlé", 2.0)]
    assert sheet["lines"][0] == {"name": "Apple", "ticker": "AAPL", "isin": "US0378331005", "weight": 5.0,
                                 "country": "USA", "sector": "Technologie", "asset_class": "Equity",
                                 "exposure_eur": 0.0}
    assert (sheet["has_full_list"], sheet["lines_count"], sheet["coverage_pct"], sheet["provider"]) == (
        True, 3, 10.0, "ishares")
    # Pays agrégés sur les lignes (et non lus dans le JSON du profil), le reste en « Non renseigné »
    assert sheet["countries"] == [{"name": "Non renseigné", "weight": 90.0}, {"name": "USA", "weight": 8.0},
                                  {"name": "CHE", "weight": 2.0}]
    assert sheet["top_holdings"] == []
    assert (sheet["profile"]["id"], sheet["exposure_profile_id"], sheet["held_value_eur"]) == (profile.id, None, 0.0)


def test_sheet_of_synthetic_uses_reference_lines(client, db_session):
    reference = _profile(db_session, "Réplique", provider="amundi", replication="physical")
    _with_lines(db_session, reference, [_line("Apple", 60.0), _line("Cash", 40.0, None, "Non renseigné", asset_class="Cash")])
    synthetic = _profile(db_session, "Swap", provider="amundi", replication="synthetic", index_name="MSCI World",
                         exposure_profile_id=reference.id)

    sheet = client.get(f"/etf-profiles/{synthetic.id}/constituents").json()

    assert (sheet["exposure_profile_id"], sheet["exposure_profile_name"]) == (reference.id, "Réplique")
    assert (sheet["profile"]["replication"], sheet["profile"]["index_name"]) == ("synthetic", "MSCI World")
    assert [x["name"] for x in sheet["lines"]] == ["Apple", "Cash"]
    assert (sheet["has_full_list"], sheet["lines_count"], sheet["coverage_pct"]) == (True, 2, 100.0)
    assert sheet["sectors"] == [{"name": "Technologie", "weight": 60.0}, {"name": "Liquidités et dérivés", "weight": 40.0}]


def test_sheet_of_synthetic_without_reference_is_empty_not_an_error(client, db_session):
    synthetic = _profile(db_session, "Swap", replication="synthetic", index_name="Indice inconnu")

    resp = client.get(f"/etf-profiles/{synthetic.id}/constituents")

    assert resp.status_code == 200
    sheet = resp.json()
    assert (sheet["lines"], sheet["has_full_list"], sheet["countries"], sheet["sectors"], sheet["coverage_pct"]) == (
        [], False, [], [], 0.0)


def test_sheet_without_lines_returns_aggregates_and_top_holdings(client, db_session):
    top = [{"name": "Apple", "ticker": "AAPL", "weight": 6.0}]
    profile = _profile(db_session, provider="justetf", sectors=json.dumps({"Finance": 30.0, "Technologie": 60.0}),
                       top_holdings=json.dumps(top))

    resp = client.get(f"/etf-profiles/{profile.id}/constituents")

    assert resp.status_code == 200
    sheet = resp.json()
    assert (sheet["lines"], sheet["has_full_list"], sheet["top_holdings"]) == ([], False, [{**top[0], "exposure_eur": 0.0}])
    assert sheet["sectors"] == [{"name": "Technologie", "weight": 60.0}, {"name": "Finance", "weight": 30.0},
                                {"name": "Non renseigné", "weight": 10.0}]
    assert sheet["countries"] == []


def test_sheet_manual_field_of_the_fund_wins_over_lines(client, db_session):
    """Même règle que le scanner de diversification : la saisie manuelle l'emporte, champ par champ."""
    profile = _profile(db_session, countries=json.dumps({"FRA": 100.0}),
                       composition_sources=json.dumps({"countries": "manual"}))
    _with_lines(db_session, profile, [_line("Apple", 100.0)])

    sheet = client.get(f"/etf-profiles/{profile.id}/constituents").json()

    assert sheet["countries"] == [{"name": "FRA", "weight": 100.0}]
    assert sheet["sectors"] == [{"name": "Technologie", "weight": 100.0}]


def test_sheet_unknown_profile_is_404(client):
    assert client.get("/etf-profiles/999/constituents").status_code == 404


def _account(db, **kw):
    account = Account(name=kw.pop("name", "PEA"), type="investissement", currency="EUR", active=True, **kw)
    db.add(account)
    db.commit()
    return account


def _holding(db, account, profile, ticker, quantity, pru=None):
    db.add(PortfolioHolding(account_id=account.id, ticker=ticker, asset_name=ticker, quantity=quantity,
                            buy_price_avg=pru, currency="EUR", etf_profile_id=profile.id))
    db.commit()


def test_sheet_held_value_sums_positions_of_this_profile(client, db_session):
    profile, other = _profile(db_session), _profile(db_session, "Autre")
    mine, second = _account(db_session), _account(db_session, name="CTO")
    third_party = _account(db_session, name="Tiers", held_for="Quelqu'un")
    _holding(db_session, mine, profile, "WLD.PA", 2.0)
    _holding(db_session, second, profile, "NOQUOTE.PA", 4.0, pru=25.0)
    _holding(db_session, third_party, profile, "WLD.PA", 50.0)
    _holding(db_session, mine, other, "OTH.PA", 7.0)

    sheet = client.get(f"/etf-profiles/{profile.id}/constituents").json()

    assert sheet["held_value_eur"] == 300.0


def test_sheet_exposure_per_line_is_computed_by_the_backend(client, db_session):
    """Exposition en € d'une ligne = poids × valeur détenue (règle n° 2 : KPI côté backend), lignes et top 10."""
    profile = _profile(db_session)
    _with_lines(db_session, profile, [_line("Apple", 5.0), _line("Dérivé", -0.5), _line("Nestlé", 1.234)])
    _holding(db_session, _account(db_session), profile, "WLD.PA", 3.0)  # 300 €
    top = _profile(db_session, "Top", top_holdings=json.dumps([{"name": "Apple", "weight": 10.0}, {"name": "Nestlé", "weight": 2.5}]))
    _holding(db_session, _account(db_session, name="CTO"), top, "TOP.PA", 2.0)  # 200 €

    sheet = client.get(f"/etf-profiles/{profile.id}/constituents").json()
    partial = client.get(f"/etf-profiles/{top.id}/constituents").json()

    assert [(x["name"], x["exposure_eur"]) for x in sheet["lines"]] == [("Apple", 15.0), ("Nestlé", 3.7), ("Dérivé", -1.5)]
    assert [x["exposure_eur"] for x in partial["top_holdings"]] == [20.0, 5.0]


def test_sheet_queries_are_constant(client, db_session, measure_queries):
    reference = _profile(db_session, "Référence")
    _with_lines(db_session, reference, [_line(f"Société {i}", 100.0 / 1500) for i in range(1500)])
    synthetic = _profile(db_session, "Swap", replication="synthetic", exposure_profile_id=reference.id)
    account = _account(db_session)
    for i in range(3):
        _holding(db_session, account, synthetic, f"SWP{i}.PA", 1.0)
    url = f"/etf-profiles/{synthetic.id}/constituents"
    db_session.expire_all()

    resp, queries = measure_queries(lambda: client.get(url))

    assert (resp.status_code, len(resp.json()["lines"])) == (200, 1500)
    assert queries <= 8


def test_exposure_of_a_line_without_numeric_weight_is_zero():
    from app.domain.etf_sheet import exposure_eur

    assert [exposure_eur(w, 200.0) for w in (None, "6", True, 6, 1.5)] == [0.0, 0.0, 0.0, 12.0, 3.0]
