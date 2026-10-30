"""Appariement des virements internes : calcul pur, sans base."""
from datetime import datetime, timedelta

from app.domain.transfers import match_pairs
from app.models.transaction import Transaction

DAY = datetime(2026, 10, 1)


def _leg(id_, account_id, type_, amount, date=DAY):
    return Transaction(id=id_, account_id=account_id, type=type_, amount=amount, date=date)


def _eur(value, account_id):
    return value


def test_match_pairs_respects_amount_tolerance():
    sortie, entree = _leg(1, 1, "Sortie", 100.0), _leg(2, 2, "Entree", 101.0)
    assert len(match_pairs([sortie], [("regular", entree)], _eur, day_tolerance=3, amount_tolerance_pct=2.0)) == 1
    assert match_pairs([sortie], [("regular", entree)], _eur, day_tolerance=3, amount_tolerance_pct=0.5) == []


def test_match_pairs_respects_day_tolerance():
    sortie, entree = _leg(1, 1, "Sortie", 100.0), _leg(2, 2, "Entree", 100.0, DAY + timedelta(days=4))
    assert match_pairs([sortie], [("regular", entree)], _eur, day_tolerance=3, amount_tolerance_pct=1.0) == []
    [pair] = match_pairs([sortie], [("regular", entree)], _eur, day_tolerance=5, amount_tolerance_pct=1.0)
    assert pair.day_gap == 4 and not pair.ambiguous


def test_match_pairs_never_pairs_same_account():
    sortie, entree = _leg(1, 1, "Sortie", 100.0), _leg(2, 1, "Entree", 100.0)
    assert match_pairs([sortie], [("regular", entree)], _eur, day_tolerance=3, amount_tolerance_pct=1.0) == []


def test_equal_candidates_are_returned_as_ambiguous():
    sortie = _leg(1, 1, "Sortie", 100.0)
    first, second = _leg(2, 2, "Entree", 100.0), _leg(3, 3, "Entree", 100.0)
    pairs = match_pairs([sortie], [("regular", first), ("regular", second)], _eur, day_tolerance=3, amount_tolerance_pct=1.0)
    assert len(pairs) == 2 and all(p.ambiguous for p in pairs)


def test_closest_entree_wins_and_serves_only_one_sortie():
    near, far = _leg(1, 1, "Sortie", 100.0), _leg(2, 1, "Sortie", 100.0, DAY - timedelta(days=2))
    entree = _leg(3, 2, "Entree", 100.0)
    [pair] = match_pairs([far, near], [("regular", entree)], _eur, day_tolerance=3, amount_tolerance_pct=1.0)
    assert pair.sortie is near
