"""Flux d'un compte titres : variations d'espèces et capital investi (flux externes depuis la référence)."""
from dataclasses import dataclass
from datetime import date as date_type, datetime

from sqlalchemy.orm import Session

from app.domain.holdings import is_trade
from app.domain.portfolio import CashEvent, classify_regular_flow
from app.models.balance_snapshot import BalanceSnapshot
from app.repositories.investissement import portfolio as repo


def cash_events(db: Session, account_id: int, after: datetime | None) -> tuple[list[CashEvent], bool]:
    """Variations d'espèces datées après `after`. Renvoie aussi si le compte a des opérations d'investissement."""
    all_txs = repo.investment_transactions(db, account_id)
    events: list[CashEvent] = []
    for tx in all_txs:
        if after is not None and tx.date <= after:
            continue
        trade = is_trade(tx.type, tx.ticker, tx.quantity)
        if tx.type == "versement":
            events.append(CashEvent(tx.date, 0.0 if trade else tx.amount, tx.amount))
        elif tx.type == "retrait":
            events.append(CashEvent(tx.date, 0.0 if trade else -tx.amount, -tx.amount))
        elif tx.type in ("vente", "dividende"):
            events.append(CashEvent(tx.date, tx.amount))
        elif tx.type in ("achat", "frais"):
            events.append(CashEvent(tx.date, -tx.amount))
    # Avec des opérations d'investissement, seuls les virements bancaires restent des flux (un virement vers
    # une assurance-vie crée une Entree, pas un versement)
    for tx in repo.regular_transactions(db, account_id, transfers_only=bool(all_txs)):
        if after is not None and tx.date <= after:
            continue
        flow = classify_regular_flow(tx)
        if flow:
            events.append(CashEvent(tx.date, flow, flow))
    events.sort(key=lambda e: e.date)
    return events, bool(all_txs)


@dataclass
class Capital:
    """Capital investi : référence (snapshot Point Zéro ou inventaire) puis flux externes datés après elle."""

    events: list[CashEvent]  # variations d'espèces après le Point Zéro des positions
    reference: BalanceSnapshot | None
    reference_date: datetime | None
    reference_value: float
    flow_events: list[CashEvent]
    external_total: float

    def invested_at(self, day: date_type) -> float:
        return self.reference_value + sum(e.external for e in self.flow_events if e.date.date() <= day)


def capital(db: Session, account_id: int, baseline_date: datetime | None) -> Capital:
    """Capital investi depuis l'origine du compte, indépendamment de la date du Point Zéro des positions :
    base = snapshot Point Zéro s'il existe (comme avant), sinon rien ; puis tous les flux externes datés après.
    """
    events, _ = cash_events(db, account_id, baseline_date)
    reference = repo.latest_zero_point(db, account_id)
    reference_date = reference.date if reference else None
    reference_value = reference.current_value if reference else 0.0
    flow_events, _ = cash_events(db, account_id, reference_date)
    flow_events = [e for e in flow_events if e.external]
    return Capital(events, reference, reference_date, reference_value, flow_events, sum(e.external for e in flow_events))


def anchor_on_inventory(cap: Capital, baseline_date: datetime | None, opening_value: float) -> None:
    """Sans snapshot Point Zéro ni versement antérieur à l'inventaire, rien ne justifie le capital déjà en
    portefeuille : on le compte comme investi à la valeur d'ouverture (sinon tout le portefeuille serait « gain »).
    """
    if cap.reference is None and baseline_date is not None and not any(e.date <= baseline_date for e in cap.flow_events):
        cap.reference_date, cap.reference_value = baseline_date, opening_value
        cap.flow_events = [e for e in cap.flow_events if e.date > baseline_date]
        cap.external_total = sum(e.external for e in cap.flow_events)
