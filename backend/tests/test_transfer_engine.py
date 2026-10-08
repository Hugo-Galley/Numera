import asyncio
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.finance import month_label_from_date
from app.core.transfers import apply_rules, find_pairs, link_pair, unlink_pair
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction
from app.models.transfer_rule import TransferRule


def run(coro):
    return asyncio.run(coro)


def make_accounts(db: Session, *specs):
    accounts = [Account(name=n, type=t, currency="EUR", active=True) for n, t in specs]
    db.add_all(accounts)
    db.commit()
    return accounts


def tx(db: Session, account, type_, amount, date, merchant="x", note=None):
    t = Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_,
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR",
        running_balance=0.0, note=note,
    )
    db.add(t)
    db.commit()
    return t


def rule(db, src, dst, **kw):
    r = TransferRule(source_account_id=src.id, dest_account_id=dst.id, **kw)
    db.add(r)
    db.commit()
    return r


def test_same_amount_to_two_accounts_pairs_by_destination(db_session: Session):
    main, livret, pea = make_accounts(db_session, ("Principal", "courant"), ("Livret A", "epargne"), ("PEA cash", "epargne"))
    d = datetime(2026, 6, 5)
    s1 = tx(db_session, main, "Sortie", 500, d, "VIR LIVRET")
    s2 = tx(db_session, main, "Sortie", 500, d, "VIR PEA")
    e1 = tx(db_session, livret, "Entree", 500, d)
    e2 = tx(db_session, pea, "Entree", 500, d)
    rule(db_session, main, livret, pattern="livret")
    rule(db_session, main, pea, pattern="pea")

    linked = run(apply_rules(db_session))

    assert len(linked) == 2
    db_session.refresh(s1); db_session.refresh(s2)
    assert s1.linked_transaction_id == e1.id
    assert s2.linked_transaction_id == e2.id
    assert s1.link_origin == "rule" and s1.transfer_rule_id is not None
    assert e1.is_transfer is True and e1.linked_transaction_id == s1.id


def test_entree_is_never_used_twice(db_session: Session):
    main, livret = make_accounts(db_session, ("Principal", "courant"), ("Livret A", "epargne"))
    s_near = tx(db_session, main, "Sortie", 500, datetime(2026, 6, 5))
    s_far = tx(db_session, main, "Sortie", 500, datetime(2026, 6, 8))
    e = tx(db_session, livret, "Entree", 500, datetime(2026, 6, 5))
    rule(db_session, main, livret)

    linked = run(apply_rules(db_session))

    assert len(linked) == 1
    db_session.refresh(s_near); db_session.refresh(s_far)
    assert s_near.linked_transaction_id == e.id
    assert s_far.linked_transaction_id is None


def test_ambiguous_tie_is_left_as_suggestion(db_session: Session):
    main, livret = make_accounts(db_session, ("Principal", "courant"), ("Livret A", "epargne"))
    d = datetime(2026, 6, 5)
    s1 = tx(db_session, main, "Sortie", 500, d)
    s2 = tx(db_session, main, "Sortie", 500, d)
    tx(db_session, livret, "Entree", 500, d)
    tx(db_session, livret, "Entree", 500, d)
    rule(db_session, main, livret)

    assert run(apply_rules(db_session)) == []
    db_session.refresh(s1); db_session.refresh(s2)
    assert s1.is_transfer is False and s2.is_transfer is False
    pairs = run(find_pairs(db_session, source_account_id=main.id, dest_account_id=livret.id))
    assert pairs and all(p.ambiguous for p in pairs)


def test_unlink_of_rule_link_is_not_relinked(db_session: Session):
    main, livret = make_accounts(db_session, ("Principal", "courant"), ("Livret A", "epargne"))
    d = datetime(2026, 6, 5)
    s = tx(db_session, main, "Sortie", 500, d)
    e = tx(db_session, livret, "Entree", 500, d)
    rule(db_session, main, livret)
    run(apply_rules(db_session))

    unlink_pair(db_session, s)
    db_session.commit()
    db_session.refresh(s); db_session.refresh(e)
    assert s.is_transfer is False and e.is_transfer is False
    assert s.is_transfer_ignored is True and e.is_transfer_ignored is True

    assert run(apply_rules(db_session)) == []


def test_manual_unlink_does_not_mark_ignored(db_session: Session):
    main, livret = make_accounts(db_session, ("Principal", "courant"), ("Livret A", "epargne"))
    d = datetime(2026, 6, 5)
    s = tx(db_session, main, "Sortie", 500, d)
    e = tx(db_session, livret, "Entree", 500, d)
    link_pair(db_session, s, e, "regular", "manual")
    db_session.commit()
    unlink_pair(db_session, s)
    db_session.commit()
    db_session.refresh(e)
    assert s.is_transfer_ignored is False and e.is_transfer_ignored is False
    assert e.link_origin is None


def test_history_beyond_six_months_and_dry_run(db_session: Session):
    main, livret = make_accounts(db_session, ("Principal", "courant"), ("Livret A", "epargne"))
    d = datetime(2023, 3, 5)
    s = tx(db_session, main, "Sortie", 300, d)
    tx(db_session, livret, "Entree", 300, d)
    rule(db_session, main, livret)

    preview = run(apply_rules(db_session, dry_run=True))
    assert len(preview) == 1
    db_session.refresh(s)
    assert s.is_transfer is False

    assert len(run(apply_rules(db_session))) == 1
    db_session.refresh(s)
    assert s.is_transfer is True


def test_investment_destination_links_versement(db_session: Session):
    main, broker = make_accounts(db_session, ("Principal", "courant"), ("Courtier", "investissement"))
    d = datetime(2026, 6, 10)
    s = tx(db_session, main, "Sortie", 1000, d)
    v = InvestmentTransaction(account_id=broker.id, date=d, type="versement", amount=1000, original_amount=1000, currency="EUR")
    db_session.add(v)
    db_session.commit()
    rule(db_session, main, broker)

    assert len(run(apply_rules(db_session))) == 1
    db_session.refresh(s); db_session.refresh(v)
    assert s.linked_investment_transaction_id == v.id
    assert v.linked_transaction_id == s.id and v.is_transfer is True and v.link_origin == "rule"


def test_pattern_and_amount_filters(db_session: Session):
    main, livret = make_accounts(db_session, ("Principal", "courant"), ("Livret A", "epargne"))
    d = datetime(2026, 6, 5)
    tx(db_session, main, "Sortie", 500, d, "AUTRE")
    tx(db_session, main, "Sortie", 120, d, "VIR LIVRET")
    tx(db_session, livret, "Entree", 500, d)
    tx(db_session, livret, "Entree", 120, d)
    rule(db_session, main, livret, pattern="livret", amount=500)
    assert run(apply_rules(db_session)) == []


def test_api_link_exposes_origin_and_partner_account(client, db_session: Session):
    main, livret = make_accounts(db_session, ("Principal", "courant"), ("Livret A", "epargne"))
    d = datetime(2026, 6, 5)
    s = tx(db_session, main, "Sortie", 500, d)
    e = tx(db_session, livret, "Entree", 500, d)
    assert client.post(f"/transactions/{s.id}/link/{e.id}").status_code == 200

    rows = client.get("/transactions", params={"is_transfer": True}).json()
    by_id = {r["id"]: r for r in rows}
    assert by_id[s.id]["linked_account_id"] == livret.id
    assert by_id[e.id]["linked_account_id"] == main.id
    assert by_id[s.id]["link_origin"] == "manual"


def test_api_ignore_marks_both_sides(client, db_session: Session):
    main, livret = make_accounts(db_session, ("Principal", "courant"), ("Livret A", "epargne"))
    d = datetime(2026, 6, 5)
    s = tx(db_session, main, "Sortie", 500, d)
    e = tx(db_session, livret, "Entree", 500, d)
    assert client.post(f"/transactions/{s.id}/ignore", params={"other_id": e.id}).status_code == 204
    db_session.refresh(s); db_session.refresh(e)
    assert s.is_transfer_ignored and e.is_transfer_ignored
    assert client.get("/transactions/potential-transfers").json() == []


def test_candidates_are_ranked_and_wide_window(client, db_session: Session):
    main, livret, pea = make_accounts(db_session, ("Principal", "courant"), ("Livret A", "epargne"), ("PEA cash", "epargne"))
    s = tx(db_session, main, "Sortie", 500, datetime(2026, 6, 5))
    far = tx(db_session, livret, "Entree", 500, datetime(2026, 6, 15))   # 10 jours
    near = tx(db_session, pea, "Entree", 505, datetime(2026, 6, 6))      # 1 jour, 1 % d'écart
    tx(db_session, pea, "Entree", 500, datetime(2026, 8, 1))             # hors fenêtre
    tx(db_session, main, "Entree", 500, datetime(2026, 6, 5))            # même compte

    rows = client.get(f"/transactions/{s.id}/transfer-candidates").json()
    assert [r["other_id"] for r in rows] == [near.id, far.id]
    assert rows[0]["sortie_id"] == s.id and rows[0]["type"] == "regular"

    only_livret = client.get(f"/transactions/{s.id}/transfer-candidates", params={"account_id": livret.id}).json()
    assert [r["other_id"] for r in only_livret] == [far.id]

    # depuis l'entrée, on retrouve la sortie, prête pour /link/{sortie}/{entrée}
    back = client.get(f"/transactions/{far.id}/transfer-candidates").json()
    assert back[0]["sortie_id"] == s.id and back[0]["other_id"] == far.id


def test_create_counterpart_links_and_recalculates(client, db_session: Session):
    main, livret = make_accounts(db_session, ("Principal", "courant"), ("Livret A", "epargne"))
    s = tx(db_session, main, "Sortie", 300, datetime(2026, 6, 5), "Vir livret")

    resp = client.post(f"/transactions/{s.id}/transfer-counterpart", json={"account_id": livret.id, "date": "2026-06-07T00:00:00"})
    assert resp.status_code == 201
    leg = db_session.get(Transaction, resp.json()["id"])
    db_session.refresh(s)
    assert leg.account_id == livret.id and leg.type == "Entree" and leg.amount == 300
    assert leg.running_balance == 300 and leg.date == datetime(2026, 6, 7)
    assert s.linked_transaction_id == leg.id and s.link_origin == "manual" and leg.is_transfer

    assert client.post(f"/transactions/{s.id}/transfer-counterpart", json={"account_id": main.id}).status_code == 422
    e = tx(db_session, livret, "Entree", 10, datetime(2026, 6, 9))
    assert client.post(f"/transactions/{e.id}/transfer-counterpart", json={"account_id": main.id}).status_code == 422
