"""Valeur d'un compte : source unique pour tous les totaux de patrimoine (audit A10).

Règle de repli :
- compte titres valorisé par ses positions → positions × cours + espèces (`services/portfolio/`) ;
- compte d'investissement / assurance-vie → dernier relevé (snapshot) daté au plus tard à `at` ;
- autre compte (courant, épargne, ancien type…) → le plus récent entre un relevé et la dernière
  opération (solde courant) ;
- compte `credit` → −capital restant dû de son prêt à la date (`core/loans.py`), dette déduite du patrimoine ;
- à défaut → dernier solde courant, sinon 0 (`source = "none"`, jamais de valeur inventée).
Tout compte actif compte dans le patrimoine, quel que soit son type.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.integrations.currency import get_exchange_rates
from app.services.comptes.loans import loan_remaining
from app.services.portfolio import positions_values_eur
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.transaction import Transaction

INVESTMENT_TYPES = ("investissement", "assurance_vie")


@dataclass(frozen=True)
class AccountValue:
    value: float  # devise du compte
    value_eur: float
    source: str  # positions | snapshot | balance | none


def active_accounts(db: Session) -> list[Account]:
    return db.query(Account).filter(Account.active.is_(True)).all()


def _latest_snapshot(db: Session, account_id: int, at: datetime) -> BalanceSnapshot | None:
    return (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id, BalanceSnapshot.date <= at)
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )


def _latest_transaction(db: Session, account_id: int, at: datetime) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id, Transaction.date <= at)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .first()
    )


async def account_values(
    db: Session, accounts: list[Account], at: datetime | None = None
) -> dict[int, AccountValue]:
    """Valeur de chaque compte à la date `at` (maintenant par défaut)."""
    now = datetime.now()
    at = at or now
    rates = await get_exchange_rates("EUR")
    # Les positions n'existent que pour la valeur courante : un mois passé garde le relevé à sa date
    positions = await positions_values_eur(db, accounts) if at.date() >= date.today() else {}

    values: dict[int, AccountValue] = {}
    for acc in accounts:
        rate = rates.get(acc.currency, 1.0) or 1.0
        if acc.type == "credit":
            remaining = loan_remaining(db, acc.id, at.date())
            if remaining is not None:
                values[acc.id] = AccountValue(-remaining, -remaining / rate, "loan")
                continue
        if acc.id in positions:
            eur = positions[acc.id]
            values[acc.id] = AccountValue(eur * rate, eur, "positions")
            continue

        snap = _latest_snapshot(db, acc.id, at)
        tx = _latest_transaction(db, acc.id, at)
        if acc.type in INVESTMENT_TYPES:
            # Un relevé fait foi ; le solde des opérations ne sert que sans relevé
            chosen = snap or tx
        elif snap and tx:
            chosen = snap if snap.date >= tx.date else tx
        else:
            chosen = snap or tx

        if chosen is None:
            values[acc.id] = AccountValue(0.0, 0.0, "none")
        elif isinstance(chosen, BalanceSnapshot):
            values[acc.id] = AccountValue(float(chosen.current_value or 0.0), float(chosen.current_value or 0.0) / rate, "snapshot")
        else:
            values[acc.id] = AccountValue(float(chosen.running_balance or 0.0), float(chosen.running_balance or 0.0) / rate, "balance")
    return values
