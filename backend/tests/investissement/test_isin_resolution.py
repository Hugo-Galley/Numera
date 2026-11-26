"""ISIN des positions retrouvé en tâche de fond : strict, jamais deviné, jamais écrasé."""
import asyncio
from datetime import datetime

import pytest

from app.models.account import Account
from app.models.etf_profile import EtfProfile
from app.models.holding_baseline_item import HoldingBaselineItem
from app.models.investment_transaction import InvestmentTransaction
from app.models.portfolio_holding import PortfolioHolding
from app.repositories.investissement import securities as securities_repo
from app.services.investissement.isin_resolution import resolve_missing_isins

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
async def test_isin_du_profil_rattache(db_session, account):
    profile = EtfProfile(name="ETF", ticker="ISRG.PA", isin=ISRG_ETF)
    db_session.add(profile)
    db_session.flush()
    h = _holding(db_session, account, "ISRG.PA", etf_profile_id=profile.id)
    assert await resolve_missing_isins(db_session) == 1
    assert h.isin == ISRG_ETF


@pytest.mark.anyio
async def test_profil_d_un_autre_titre_ignore(db_session, account):
    profile = EtfProfile(name="ETF", ticker="OTHER", isin=ISRG_ETF)
    db_session.add(profile)
    db_session.flush()
    h = _holding(db_session, account, "ISRG.PA")  # aucun rattachement, aucune correspondance exacte
    assert await resolve_missing_isins(db_session) == 0
    assert h.isin is None


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
