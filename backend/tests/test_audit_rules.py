"""Centre d'Actions : registre ordonné de règles, une règle en échec n'emporte pas les autres."""
import asyncio

import app.services.audit as audit
from app.models.account import Account
from app.models.transaction import Transaction
from datetime import datetime

EXPECTED_ORDER = [
    "uncategorized", "duplicates", "missing_snapshots", "missing_salary", "unmatched_transfers",
    "unallocated_reimbursements", "budget", "rule_suggestions", "merchant_suggestions", "dividends",
    "broker_reconciliation", "subscription_prices", "backups",
]


def test_rules_registry_order():
    assert [rule.name for rule in audit.RULES] == EXPECTED_ORDER


def test_failing_rule_does_not_break_action_center(db_session, monkeypatch):
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.flush()
    db_session.add(Transaction(
        account_id=account.id, date=datetime(2026, 1, 5), month_label="2026-01", type="Sortie", merchant="X",
        amount=10.0, currency="EUR", original_amount=10.0, running_balance=-10.0,
    ))
    db_session.commit()

    def boom(ctx):
        raise RuntimeError("règle cassée")

    monkeypatch.setattr(audit, "RULES", [audit.Rule("boom", boom), *audit.RULES])
    response = asyncio.run(audit.compute_action_center(db_session))

    assert "uncategorized-expenses" in {action.id for action in response.actions}
