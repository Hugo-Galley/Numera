"""ISIN des positions retrouvé en tâche de fond : strict, jamais deviné, jamais écrasé."""
import asyncio
import json
from datetime import datetime

import pytest

from app.models.account import Account
from app.models.etf_profile import EtfProfile
from app.models.holding_baseline_item import HoldingBaselineItem
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.repositories.investissement import securities as securities_repo
from app.services.investissement.isin_resolution import copy_isins_to_profiles, resolve_missing_isins

AAPL = "US0378331005"
ISRG_ETF = "FR001400SDL2"
SG_ETF = "IE0002XZSHO1"


@pytest.fixture()
def account(db_session):
    acc = Account(name="CTO", type="investissement", currency="EUR", active=True)
    db_session.add(acc)
    db_session.flush()
    return acc


def _holding(db, account, ticker, isin=None, **kw):
    h = PortfolioHolding(account_id=account.id, ticker=ticker, isin=isin, asset_name=ticker, quantity=1.0, **kw)
    db.add(h)
    db.flush()
    return h


class FakeCatalog:
    def __init__(self, answers=None, error=None):
        self.answers, self.error, self.calls = answers or {}, error, []

    async def find_isin_by_ticker(self, symbol):
        self.calls.append(symbol)
        if self.error:
            raise self.error
        return self.answers.get(symbol)


@pytest.mark.anyio
async def test_isin_recopie_depuis_une_operation_du_meme_ticker(db_session, account):
    h = _holding(db_session, account, "XYZ.PA")
    db_session.add(InvestmentTransaction(account_id=account.id, date=datetime(2026, 1, 2), type="achat", amount=1, original_amount=1,
                                         ticker="xyz.pa", isin=AAPL, quantity=1))
    db_session.flush()
    assert await resolve_missing_isins(db_session) == 1
    assert h.isin == AAPL


@pytest.mark.anyio
async def test_isin_recopie_depuis_l_inventaire(db_session, account):
    h = _holding(db_session, account, "XYZ.PA")
    db_session.add(HoldingBaselineItem(account_id=account.id, baseline_date=datetime(2026, 1, 1), ticker="XYZ.PA",
                                       isin=AAPL, asset_name="X", quantity=1))
    db_session.flush()
    assert await resolve_missing_isins(db_session) == 1
    assert h.isin == AAPL


@pytest.mark.anyio
async def test_isins_contradictoires_ou_autre_compte_ignores(db_session, account):
    other = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(other)
    db_session.flush()
    h = _holding(db_session, account, "XYZ.PA")
    for isin in (AAPL, ISRG_ETF):
        db_session.add(InvestmentTransaction(account_id=account.id, date=datetime(2026, 1, 2), type="achat", amount=1,
                                             original_amount=1, ticker="XYZ.PA", isin=isin, quantity=1))
    db_session.add(InvestmentTransaction(account_id=other.id, date=datetime(2026, 1, 2), type="achat", amount=1,
                                         original_amount=1, ticker="XYZ.PA", isin=SG_ETF, quantity=1))
    db_session.flush()
    assert await resolve_missing_isins(db_session) == 0
    assert h.isin is None


@pytest.mark.anyio
async def test_isin_invalide_sur_operation_ignore(db_session, account):
    h = _holding(db_session, account, "XYZ.PA")
    db_session.add(InvestmentTransaction(account_id=account.id, date=datetime(2026, 1, 2), type="achat", amount=1,
                                         original_amount=1, ticker="XYZ.PA", isin="US0378331004", quantity=1))
    db_session.flush()
    assert await resolve_missing_isins(db_session) == 0
    assert h.isin is None


@pytest.mark.anyio
async def test_isin_du_profil_dont_le_ticker_est_celui_de_la_position(db_session, account):
    db_session.add(EtfProfile(name="MSCI World", ticker="CW8.PA", isin="LU1681043599", aliases='["CW8"]'))
    db_session.flush()
    h = _holding(db_session, account, "CW8.PA")  # non rattachée, mais ticker exact
    alias = _holding(db_session, account, "CW8")
    assert await resolve_missing_isins(db_session) == 2
    assert h.isin == alias.isin == "LU1681043599"


@pytest.mark.anyio
async def test_profil_seulement_rattache_n_est_pas_une_source(db_session, account):
    profile = EtfProfile(name="MSCI World", ticker="CW8.PA", isin="LU1681043599", aliases="[]")
    db_session.add(profile)
    db_session.flush()
    h = _holding(db_session, account, "MWRD.PA", etf_profile_id=profile.id)  # lien hérité du rapprochement par nom
    assert await resolve_missing_isins(db_session) == 0
    assert h.isin is None


@pytest.mark.anyio
async def test_profils_en_conflit_ne_donnent_rien(db_session, account):
    db_session.add_all([EtfProfile(name="A", ticker="X", isin="LU1681043599", aliases="[]"),
                        EtfProfile(name="B", ticker="Y", isin=ISRG_ETF, aliases='["x"]')])
    h = _holding(db_session, account, "X")
    assert await resolve_missing_isins(db_session) == 0
    assert h.isin is None


@pytest.mark.anyio
async def test_profils_d_accord_donnent_leur_isin(db_session, account):
    db_session.add_all([EtfProfile(name="A", ticker="X", isin=ISRG_ETF, aliases="[]"),
                        EtfProfile(name="B", ticker="Y", isin=ISRG_ETF, aliases='["x"]')])
    h = _holding(db_session, account, "X")
    assert await resolve_missing_isins(db_session) == 1
    assert h.isin == ISRG_ETF


@pytest.mark.anyio
async def test_commit_false_laisse_la_transaction_a_l_appelant(db_session, account):
    h = _holding(db_session, account, "IE0002XZSHO1.SG")
    db_session.commit()
    assert await resolve_missing_isins(db_session, commit=False) == 1
    assert h.isin == SG_ETF
    db_session.rollback()
    db_session.refresh(h)
    assert h.isin is None


@pytest.mark.anyio
async def test_filtre_par_compte(db_session, account):
    other = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(other)
    db_session.flush()
    mine, theirs = _holding(db_session, account, "IE0002XZSHO1.SG"), _holding(db_session, other, "IE0002XZSHO1.SG")
    assert await resolve_missing_isins(db_session, account_id=account.id) == 1
    assert (mine.isin, theirs.isin) == (SG_ETF, None)


@pytest.mark.anyio
async def test_classe_d_actions_a_point_cherchee_sous_son_ticker_entier(db_session, account):
    securities_repo.upsert_many(db_session, [
        {"isin": "US0846707026", "ticker": "BRK.B", "name": "Berkshire", "source": "ishares", "exchange": "NYSE"}])
    h = _holding(db_session, account, "BRK.B")
    assert await resolve_missing_isins(db_session) == 1
    assert h.isin == "US0846707026"


@pytest.mark.anyio
async def test_isin_dans_le_symbole(db_session, account):
    h = _holding(db_session, account, "IE0002XZSHO1.SG")
    assert await resolve_missing_isins(db_session) == 1
    assert h.isin == SG_ETF


@pytest.mark.anyio
async def test_catalogue_simule(db_session, account):
    h = _holding(db_session, account, "ISRG.PA")
    catalog = FakeCatalog({"ISRG.PA": ISRG_ETF})
    assert await resolve_missing_isins(db_session, [catalog]) == 1
    assert h.isin == ISRG_ETF


@pytest.mark.anyio
async def test_reponse_invalide_du_catalogue_refusee(db_session, account):
    h = _holding(db_session, account, "ISRG.PA")
    assert await resolve_missing_isins(db_session, [FakeCatalog({"ISRG.PA": "FR001400SDL3"})]) == 0
    assert h.isin is None


@pytest.mark.anyio
async def test_catalogue_en_erreur_ignore_et_suivant_essaye(db_session, account):
    h = _holding(db_session, account, "ISRG.PA")
    broken, good = FakeCatalog(error=RuntimeError("boom")), FakeCatalog({"ISRG.PA": ISRG_ETF})
    assert await resolve_missing_isins(db_session, [broken, good]) == 1
    assert h.isin == ISRG_ETF


@pytest.mark.anyio
async def test_referentiel_des_titres(db_session, account):
    securities_repo.upsert_many(db_session, [
        {"isin": AAPL, "ticker": "AAPL", "name": "Apple", "source": "ishares", "exchange": "NASDAQ"}])
    h = _holding(db_session, account, "AAPL")
    assert await resolve_missing_isins(db_session) == 1
    assert h.isin == AAPL


@pytest.mark.anyio
async def test_referentiel_place_incompatible_reste_vide(db_session, account):
    securities_repo.upsert_many(db_session, [
        {"isin": AAPL, "ticker": "ISRG", "name": "Intuitive", "source": "ishares", "exchange": "NASDAQ"}])
    h = _holding(db_session, account, "ISRG.PA")
    assert await resolve_missing_isins(db_session) == 0
    assert h.isin is None


@pytest.mark.anyio
async def test_manual_isin_is_kept(db_session, account):
    securities_repo.upsert_many(db_session, [
        {"isin": AAPL, "ticker": "AAPL", "name": "Apple", "source": "ishares", "exchange": "NASDAQ"}])
    h = _holding(db_session, account, "AAPL", isin=ISRG_ETF)
    catalog = FakeCatalog({"AAPL": SG_ETF})
    assert await resolve_missing_isins(db_session, [catalog]) == 0
    assert h.isin == ISRG_ETF
    assert catalog.calls == []


@pytest.mark.anyio
async def test_aucun_candidat_sur_reste_vide(db_session, account):
    h = _holding(db_session, account, "ZZZ.PA")
    assert await resolve_missing_isins(db_session, [FakeCatalog()]) == 0
    assert h.isin is None


def test_lectures_groupees(db_session, account, measure_queries):
    for i in range(30):
        _holding(db_session, account, f"T{i}.PA")
    n, queries = measure_queries(lambda: asyncio.run(resolve_missing_isins(db_session)))
    assert n == 0
    assert queries <= 8


WORLD = "IE00B4L5Y983"


def _bare_profile(db, ticker, isin=None, aliases=None, refreshed=True):
    p = EtfProfile(name=ticker, ticker=ticker, isin=isin, aliases=json.dumps(aliases or [ticker]),
                   composition_refreshed_at=datetime(2026, 11, 26) if refreshed else None)
    db.add(p)
    db.flush()
    return p


def test_isin_de_la_position_recopie_sur_son_profil(db_session, account):
    profile = _bare_profile(db_session, "SWDA.L")
    _holding(db_session, account, "SWDA.L", isin=WORLD, etf_profile_id=profile.id)
    assert copy_isins_to_profiles(db_session) == 1
    db_session.expire_all()
    assert profile.isin == WORLD
    assert profile.composition_refreshed_at is None  # relu chez l'émetteur au prochain passage


def test_isin_recopie_par_alias_exact(db_session, account):
    profile = _bare_profile(db_session, "IWDA.AS", aliases=["IWDA.AS", "SWDA.L"])
    _holding(db_session, account, "SWDA.L", isin=WORLD, etf_profile_id=profile.id)
    assert copy_isins_to_profiles(db_session) == 1
    assert profile.isin == WORLD


def test_isin_du_profil_jamais_remplace(db_session, account):
    profile = _bare_profile(db_session, "SWDA.L", isin=SG_ETF)
    _holding(db_session, account, "SWDA.L", isin=WORLD, etf_profile_id=profile.id)
    assert copy_isins_to_profiles(db_session) == 0
    assert profile.isin == SG_ETF


def test_isins_divergents_aucun_recopie(db_session, account):
    other = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add(other)
    db_session.flush()
    profile = _bare_profile(db_session, "SWDA.L")
    _holding(db_session, account, "SWDA.L", isin=WORLD, etf_profile_id=profile.id)
    _holding(db_session, other, "SWDA.L", isin=SG_ETF, etf_profile_id=profile.id)
    assert copy_isins_to_profiles(db_session) == 0
    assert profile.isin is None


def test_rattachement_sans_ticker_commun_ne_prouve_rien(db_session, account):
    """Un rattachement hérité de l'ancien rapprochement par nom ne donne pas son ISIN au profil."""
    profile = _bare_profile(db_session, "CW8.PA")
    _holding(db_session, account, "SWDA.L", isin=WORLD, etf_profile_id=profile.id)
    assert copy_isins_to_profiles(db_session) == 0
    assert profile.isin is None


def test_isin_deja_porte_par_un_autre_profil_non_recopie(db_session, account):
    _bare_profile(db_session, "IWDA.AS", isin=WORLD)
    profile = _bare_profile(db_session, "SWDA.L")
    _holding(db_session, account, "SWDA.L", isin=WORLD, etf_profile_id=profile.id)
    assert copy_isins_to_profiles(db_session) == 0
    assert profile.isin is None


def test_isin_invalide_non_recopie(db_session, account):
    profile = _bare_profile(db_session, "SWDA.L")
    _holding(db_session, account, "SWDA.L", isin="IE00B4L5Y984", etf_profile_id=profile.id)
    assert copy_isins_to_profiles(db_session) == 0


@pytest.mark.anyio
async def test_isin_resolu_recopie_sur_le_profil(db_session, account):
    profile = _bare_profile(db_session, "SWDA.L")
    h = _holding(db_session, account, "SWDA.L", etf_profile_id=profile.id)
    await resolve_missing_isins(db_session, [FakeCatalog({"SWDA.L": WORLD})])
    db_session.expire_all()
    assert (h.isin, profile.isin) == (WORLD, WORLD)


def test_recopie_en_masse(db_session, account, measure_queries):
    def count_for(size):
        for i in range(size):
            p = _bare_profile(db_session, f"E{size}X{i}.L")
            _holding(db_session, account, p.ticker, isin=None, etf_profile_id=p.id)
        _, queries = measure_queries(lambda: copy_isins_to_profiles(db_session))
        return queries

    assert count_for(2) == count_for(40)
