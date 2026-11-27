"""Chaque position est décrite par le profil de son propre fonds (son ISIN), jamais par celui d'un autre."""
import pytest

from app.domain.etf_attachment import HoldingRef, ProfileRef, plan_attachments
from app.models.account import Account
from app.models.etf_profile import EtfProfile
from app.models.portfolio_holding import PortfolioHolding
from app.services.investissement.etf_attachment import attach_to_own_profiles
from app.services.investissement.isin_resolution import resolve_missing_isins

CW8 = "LU1681043599"
WPEA = "IE0002XZSHO1"
NEW = "IE000BI8OT95"


def _profile(pid, ticker, isin, aliases=None, is_system=False):
    return ProfileRef(pid, ticker, isin, aliases or [ticker], is_system)


def test_holding_with_isin_moves_to_its_own_profile():
    plan = plan_attachments([HoldingRef(10, "WPEA.PA", WPEA, 1)], [_profile(1, "CW8.PA", CW8), _profile(2, "WPEA.PA", WPEA)])
    assert plan.moves == {10: 2}
    assert (plan.create_isins, plan.pending, plan.detach) == (set(), {}, set())


def test_missing_profile_is_created_once_for_two_holdings():
    holdings = [HoldingRef(10, "AAA.PA", NEW, 1), HoldingRef(11, "AAA.DE", NEW, 1)]
    plan = plan_attachments(holdings, [_profile(1, "CW8.PA", CW8)])
    assert plan.create_isins == {NEW}
    assert plan.pending == {10: NEW, 11: NEW}
    assert plan.moves == {}


def test_holding_without_isin_on_system_profile_is_detached_unless_ticker_matches():
    system = _profile(1, "CW8.PA", CW8, ["CW8", "cw8.pa"], is_system=True)
    holdings = [HoldingRef(10, "CW8.PA", None, 1), HoldingRef(11, "cw8", None, 1), HoldingRef(12, "XYZ.PA", None, 1)]
    plan = plan_attachments(holdings, [system])
    assert plan.detach == {12}
    assert (plan.moves, plan.create_isins) == ({}, set())


def test_holding_without_isin_on_manual_profile_stays_attached():
    plan = plan_attachments([HoldingRef(12, "XYZ.PA", None, 1)], [_profile(1, "CW8.PA", CW8)])
    assert plan.detach == set()


def test_already_on_own_profile_is_untouched():
    plan = plan_attachments(
        [HoldingRef(10, "CW8.PA", CW8, 1)], [_profile(1, "CW8.PA", CW8, is_system=True), _profile(2, "AUTRE", CW8)])
    assert (plan.moves, plan.create_isins, plan.pending, plan.detach) == ({}, set(), {}, set())


def test_unattached_holding_joins_existing_profile_but_never_creates_one():
    """Une action en direct a aussi un ISIN : sans profil qui le porte, rien n'est créé."""
    plan = plan_attachments(
        [HoldingRef(10, "WPEA.PA", WPEA, None), HoldingRef(11, "TTE.PA", "FR0000120271", None)],
        [_profile(2, "WPEA.PA", WPEA)])
    assert plan.moves == {10: 2}
    assert (plan.create_isins, plan.pending) == (set(), {})


def test_isin_held_in_the_symbol_counts_and_an_invalid_isin_does_not():
    profiles = [_profile(1, "CW8.PA", CW8)]
    plan = plan_attachments([HoldingRef(10, f"{WPEA}.SG", None, 1), HoldingRef(11, "CW8.PA", "FAUX", 1)], profiles)
    assert plan.pending == {10: WPEA}
    assert plan.detach == set()


@pytest.fixture()
def account(db_session):
    acc = Account(name="CTO", type="investissement", currency="EUR", active=True)
    db_session.add(acc)
    db_session.flush()
    return acc


def _db_profile(db, name, ticker, isin, is_system=False):
    profile = EtfProfile(name=name, ticker=ticker, isin=isin, aliases=f'["{ticker}"]', is_system=is_system)
    db.add(profile)
    db.flush()
    return profile


def _holding(db, account, ticker, isin=None, profile_id=None):
    holding = PortfolioHolding(account_id=account.id, ticker=ticker, isin=isin, asset_name=f"Nom {ticker}",
                               quantity=1.0, etf_profile_id=profile_id)
    db.add(holding)
    db.flush()
    return holding


def test_attach_to_own_profiles_moves_holdings_in_db(db_session, account):
    system = _db_profile(db_session, "MSCI World", "CW8.PA", CW8, is_system=True)
    moved = _holding(db_session, account, "AAA.PA", NEW, system.id)
    kept = _holding(db_session, account, "CW8.PA", None, system.id)
    detached = _holding(db_session, account, "XYZ.PA", None, system.id)

    assert attach_to_own_profiles(db_session) == 2
    db_session.expire_all()

    own = db_session.query(EtfProfile).filter(EtfProfile.isin == NEW).one()
    assert (own.name, own.ticker, own.is_system, own.composition_refreshed_at) == ("Nom AAA.PA", "AAA.PA", False, None)
    assert (own.countries, own.sectors, own.top_holdings, own.lines_count) == ("{}", "{}", "[]", 0)
    assert (moved.etf_profile_id, kept.etf_profile_id, detached.etf_profile_id) == (own.id, system.id, None)
    assert attach_to_own_profiles(db_session) == 0


def test_attach_without_commit_updates_loaded_objects(db_session, account):
    other = _db_profile(db_session, "CW8", "CW8.PA", CW8)
    holding = _holding(db_session, account, "AAA.PA", NEW, other.id)
    db_session.commit()
    assert holding.etf_profile_id == other.id

    attach_to_own_profiles(db_session, commit=False)

    own = db_session.query(EtfProfile).filter(EtfProfile.isin == NEW).one()
    assert holding.etf_profile_id == own.id
    db_session.rollback()
    assert db_session.query(EtfProfile).filter(EtfProfile.isin == NEW).count() == 0


def test_attach_runs_in_constant_queries(db_session, account, measure_queries):
    other = _db_profile(db_session, "CW8", "CW8.PA", CW8)
    isins = [NEW, WPEA, "IE00B4L5Y983", "IE00B5BMR087", "FR0011550185"]
    for i in range(200):
        _holding(db_session, account, f"T{i}.PA", isins[i % len(isins)], other.id)
    db_session.commit()

    changed, queries = measure_queries(lambda: attach_to_own_profiles(db_session))

    assert changed == 200
    assert queries <= 6


@pytest.mark.anyio
async def test_resolve_missing_isins_attaches_holding_to_its_fund(db_session, account):
    other = _db_profile(db_session, "CW8", "CW8.PA", CW8)
    holding = _holding(db_session, account, f"{WPEA}.SG", None, other.id)

    assert await resolve_missing_isins(db_session) == 1
    db_session.expire_all()

    assert db_session.query(EtfProfile).filter(EtfProfile.isin == WPEA).one().id == holding.etf_profile_id


@pytest.mark.anyio
async def test_resolve_attaches_even_when_no_isin_is_missing(db_session, account):
    other = _db_profile(db_session, "CW8", "CW8.PA", CW8)
    holding = _holding(db_session, account, "AAA.PA", NEW, other.id)

    assert await resolve_missing_isins(db_session) == 0
    db_session.rollback()  # le passage a déjà validé

    assert db_session.query(EtfProfile).filter(EtfProfile.isin == NEW).one().id == holding.etf_profile_id
