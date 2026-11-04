"""Valeur d'un compte : source unique pour tous les totaux de patrimoine (audit A10).

Règle de repli :
- compte titres valorisé par ses positions → positions × cours + espèces (`services/portfolio/`) ;
- compte d'investissement / assurance-vie → dernier relevé (snapshot) daté avant `at` (exclu) ;
- autre compte (courant, épargne, ancien type…) → le plus récent entre un relevé et la dernière
  opération (solde courant) ;
- compte `credit` → −capital restant dû de son prêt à la date (`core/loans.py`), dette déduite du patrimoine ;
- à défaut → dernier solde courant, sinon 0 (`source = "none"`, jamais de valeur inventée).
Tout compte actif compte dans le patrimoine, quel que soit son type.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.time import end_of_today
from app.integrations.currency import get_exchange_rates
from app.models.account import Account
from app.repositories.comptes import balances as repo
from app.services.comptes.loans import loan_remaining
from app.services.investissement.portfolio import positions_values_eur

INVESTMENT_TYPES = ("investissement", "assurance_vie")


@dataclass(frozen=True)
class AccountValue:
    value: float  # devise du compte
    value_eur: float
    source: str  # positions | snapshot | balance | loan | none
    as_of: datetime | None = None  # date du relevé / de la dernière opération retenue


async def account_values(
    db: Session, accounts: list[Account], at: datetime | None = None, use_positions: bool = True
) -> dict[int, AccountValue]:
    """Valeur de chaque compte à `at` (borne exclusive ; fin de la journée en cours par défaut).

    `use_positions=False` : vue qui compare des relevés (mois d'investissements) et ignore la valorisation
    par positions. Relevés et soldes sont lus par lot (une requête chacun, quel que soit le nombre de comptes).
    """
    at = at or end_of_today()
    rates = await get_exchange_rates("EUR")
    # Les positions n'existent que pour la valeur courante : un mois passé garde le relevé à sa date
    positions = await positions_values_eur(db, accounts) if use_positions and at >= end_of_today() else {}
    plain = [a.id for a in accounts if a.type != "credit" and a.id not in positions]
    snapshots = repo.latest_snapshots_by_account(db, plain, at)
    balances = repo.latest_balances_by_account(db, plain, at)

    values: dict[int, AccountValue] = {}
    for acc in accounts:
        rate = rates.get(acc.currency, 1.0) or 1.0
        if acc.type == "credit":
            remaining = loan_remaining(db, acc.id, (at - timedelta(microseconds=1)).date())
            if remaining is not None:
                values[acc.id] = AccountValue(-remaining, -remaining / rate, "loan")
                continue
        if acc.id in positions:
            eur = positions[acc.id]
            values[acc.id] = AccountValue(eur * rate, eur, "positions")
            continue

        snap, tx = snapshots.get(acc.id), balances.get(acc.id)
        # Investissement : un relevé fait foi, le solde des opérations ne sert que sans relevé ; sinon le plus récent des deux
        use_snapshot = snap is not None and (acc.type in INVESTMENT_TYPES or tx is None or snap.date >= tx.date)

        if snap is not None and use_snapshot:
            value = float(snap.current_value or 0.0)
            values[acc.id] = AccountValue(value, value / rate, "snapshot", snap.date)
        elif tx is not None:
            value = float(tx.running_balance or 0.0)
            values[acc.id] = AccountValue(value, value / rate, "balance", tx.date)
        else:
            values[acc.id] = AccountValue(0.0, 0.0, "none")
    return values
