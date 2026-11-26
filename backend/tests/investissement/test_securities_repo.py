"""Référentiel des titres : upsert en masse, lecture par ISIN et par ticker."""
from app.models.security import Security
from app.repositories.investissement import securities as repo


def _row(isin, ticker="AAA", **kw):
    return {"isin": isin, "ticker": ticker, "name": f"Titre {isin}", "source": "ishares", **kw}


def test_upsert_mille_lignes_en_une_requete(db_session, measure_queries):
    rows = [_row(f"US{i:010d}") for i in range(1000)]
    _, queries = measure_queries(lambda: repo.upsert_many(db_session, rows))
    assert queries <= 2
    assert db_session.query(Security).count() == 1000


def test_upsert_liste_vide_ne_fait_rien(db_session, measure_queries):
    _, queries = measure_queries(lambda: repo.upsert_many(db_session, []))
    assert queries == 0


def test_upsert_met_a_jour_sans_ecraser_pays_ni_secteur_par_null(db_session):
    repo.upsert_many(db_session, [_row("US0000000001", country="USA", sector="Technologie")])
    repo.upsert_many(db_session, [_row("US0000000001", ticker="NEW", country=None, sector=None, exchange="NASDAQ")])
    s = repo.by_isins(db_session, ["US0000000001"])["US0000000001"]
    assert (s.ticker, s.exchange, s.country, s.sector) == ("NEW", "NASDAQ", "USA", "Technologie")
    repo.upsert_many(db_session, [_row("US0000000001", country="FRA", sector="Finance")])
    db_session.expire_all()
    s = repo.by_isins(db_session, ["US0000000001"])["US0000000001"]
    assert (s.country, s.sector) == ("FRA", "Finance")


def test_ligne_manual_n_est_pas_reecrite(db_session):
    repo.upsert_many(db_session, [_row("US0000000002", ticker="MAN", country="USA", source="manual")])
    repo.upsert_many(db_session, [_row("US0000000002", ticker="AUTO", country="FRA", source="ishares")])
    db_session.expire_all()
    s = repo.by_isins(db_session, ["US0000000002"])["US0000000002"]
    assert (s.ticker, s.country, s.source) == ("MAN", "USA", "manual")


def test_by_ticker_renvoie_toutes_les_places(db_session):
    repo.upsert_many(db_session, [
        _row("CH0000000001", ticker="HO", exchange="PAR"),
        _row("US0000000003", ticker="HO", exchange="NYSE"),
        _row("US0000000004", ticker="OTHER"),
    ])
    assert {s.isin for s in repo.by_ticker(db_session, "HO")} == {"CH0000000001", "US0000000003"}
    assert repo.by_ticker(db_session, "ZZZ") == []


def test_by_isins_vide_et_inconnus(db_session):
    assert repo.by_isins(db_session, []) == {}
    assert repo.by_isins(db_session, ["XX0000000000"]) == {}
