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
CSCO = "US17275R1023"


def _profile(pid, ticker, isin, is_system=False):
    return ProfileRef(pid, ticker, isin, is_system)


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


def test_unattached_holding_joins_a_profile_created_in_the_same_pass():
    """Le profil créé pour une position rattachée sert aussi à la position non rattachée du même ISIN, quel que
    soit l'ordre ; seule, elle n'en ferait pas créer."""
    holdings = [HoldingRef(9, "SOLO.PA", NEW, None), HoldingRef(10, "AAA.PA", NEW, 1)]
    plan = plan_attachments(holdings, [_profile(1, "CW8.PA", CW8)])
    assert (plan.create_isins, plan.pending) == ({NEW}, {9: NEW, 10: NEW})


def test_holding_without_isin_on_system_profile_is_detached_unless_it_is_the_profile_own_ticker():
    """Les alias livrés mélangeaient plusieurs fonds : seul le ticker propre du profil système compte."""
    system = _profile(1, "CW8.PA", CW8, is_system=True)
    holdings = [HoldingRef(10, "CW8.PA", None, 1), HoldingRef(11, "cw8.pa", None, 1), HoldingRef(12, "XYZ.PA", None, 1),
                HoldingRef(13, "WPEA.PA", None, 1), HoldingRef(14, "AHYQ.DE", None, 1), HoldingRef(15, "CW8", None, 1)]
    plan = plan_attachments(holdings, [system])
    assert plan.detach == {12, 13, 14, 15}
    assert (plan.moves, plan.create_isins) == ({}, set())


def test_holding_with_isin_on_manual_profile_without_isin_stays():
    """Un profil saisi sans ISIN est un rattachement manuel : la position n'en part pas."""
    plan = plan_attachments([HoldingRef(10, "MAN.PA", NEW, 1)], [_profile(1, "MAN.PA", None)])
    assert (plan.moves, plan.create_isins, plan.pending, plan.detach) == ({}, set(), {}, set())


def test_stock_on_a_manual_profile_or_unattached_never_gets_an_etf_profile():
    """Cas CSCO : une action en direct a aussi un ISIN ; ni rattachée ni non rattachée, elle ne crée de profil."""
    plan = plan_attachments([HoldingRef(10, "CSCO", CSCO, 28), HoldingRef(11, "CSCO", CSCO, None)],
                            [_profile(28, "CISCO CDR", None)])
    assert (plan.moves, plan.create_isins, plan.pending, plan.detach) == ({}, set(), {}, set())


def test_holding_with_isin_leaves_a_system_profile_without_isin():
    plan = plan_attachments([HoldingRef(10, "AAA.PA", NEW, 1)], [_profile(1, "WORLD", None, is_system=True)])
    assert (plan.create_isins, plan.pending) == ({NEW}, {10: NEW})


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


def test_attach_leaves_a_stock_on_a_manual_profile_alone(db_session, account):
    """Cas CSCO de la vraie base : profil « CISCO CDR » sans ISIN, action CSCO avec son ISIN."""
    cisco = _db_profile(db_session, "CISCO CDR", "CSCO.NE", None)
    attached = _holding(db_session, account, "CSCO", CSCO, cisco.id)
    alone = _holding(db_session, account, "CSCO.DE", CSCO, None)
    db_session.commit()

    assert attach_to_own_profiles(db_session) == 0
    db_session.expire_all()

    assert (attached.etf_profile_id, alone.etf_profile_id) == (cisco.id, None)
    assert db_session.query(EtfProfile).count() == 1


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
