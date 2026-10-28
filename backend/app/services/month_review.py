"""Logique de la revue de fin de mois : bornes, étape 1, top dépenses, lecture « hors exceptionnel »."""
import json
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.budget_period import period_bounds
from app.integrations.currency import get_exchange_rates
from app.core.time import utcnow_naive
from app.domain.transactions import net_amount
from app.models.account import Account
from app.models.category import Category
from app.models.month_closure import MonthClosure
from app.models.transaction import Transaction
from app.repositories import month_review as repo
from app.repositories.analytics.common import NET_AMOUNT, ticket_restaurant_account_ids
from app.schemas.month_review import CloseRequest, ClosureRead
from app.services.accounts import account_balance
from app.services.analytics.budget import compute_budget, compute_budget_alerts

# Même liste que budget_analytics : ces catégories ne sont pas de la consommation
INVESTMENT_CATEGORIES = ["Investissement", "Epargne"]
CATEGORIZE_LIMIT = 50
TOP_EXPENSES_LIMIT = 10


def month_bounds(db: Session, year: int, month: int) -> tuple[datetime, datetime]:
    return period_bounds(db, year, month)


def exceptional_expenses(
    db: Session,
    start: datetime,
    end: datetime,
    rates: dict[str, float],
    account_id: int | None = None,
) -> float:
    """Dépenses nettes marquées exceptionnelles, hors catégories d'investissement (déjà exclues des dépenses réelles)."""

    query = (
        db.query(Account.currency, func.coalesce(func.sum(NET_AMOUNT), 0.0))
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.is_exceptional.is_(True),
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
            or_(Category.name.is_(None), Category.name.notin_(INVESTMENT_CATEGORIES)),
        )
    )
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    else:
        query = query.filter(Account.type.in_(["courant", "epargne"]))
        tr_accounts = ticket_restaurant_account_ids(db)
        if tr_accounts:
            query = query.filter(Transaction.account_id.notin_(tr_accounts))
    rows = query.group_by(Account.currency).all()
    return float(sum(total / rates.get(currency, 1.0) for currency, total in rows))


def savings_basis(budget: dict, account_scope: bool = False) -> float:
    """Montant épargné, numérateur du taux d'épargne de `budget_analytics`.

    Vue globale : revenus − dépenses réelles (l'argent investi ou mis de côté compte comme épargné).
    Vue d'un compte : revenus − dépenses du compte.
    """
    if account_scope:
        return float(budget["revenus_apres_depenses"])
    return float(budget["revenus_totaux"]) - float(budget["depenses_reelles"])


def without_exceptional(budget: dict, exceptional: float, account_scope: bool = False) -> dict:
    """Lecture « hors exceptionnel » à partir du dict de `budget_analytics` ; les totaux officiels ne bougent pas.

    Le taux officiel est plafonné à ±100 : on le recalcule depuis les montants bruts, avec le même numérateur
    que `budget_analytics` (vue globale : revenus − dépenses réelles ; vue d'un compte : revenus − dépenses).
    """
    real = float(budget["depenses_reelles"])
    income = float(budget["revenus_totaux"])
    real_excl = real - exceptional
    savings_excl = savings_basis(budget, account_scope) + exceptional
    rate_excl = savings_excl / income * 100.0 if income > 0 else 0.0
    burn_excl = float(budget["burn_rate"]) * (real_excl / real) if real > 0 else 0.0
    return {
        "exceptional_expenses": round(exceptional, 2),
        "real_expenses_excl_exceptional": round(real_excl, 2),
        "savings_excl_exceptional": round(savings_excl, 2),
        "savings_rate_excl_exceptional": round(max(min(rate_excl, 100.0), -100.0), 2),
        "burn_rate_excl_exceptional": round(max(burn_excl, 0.0), 2),
    }


def _review_tx(tx: Transaction) -> dict:

    return {
        "id": tx.id,
        "date": tx.date,
        "merchant": tx.merchant,
        "amount": round(net_amount(tx), 2),
        "category_name": tx.category.name if tx.category else None,
        "is_exceptional": bool(tx.is_exceptional),
    }


def tx_count(db: Session, start: datetime, end: datetime) -> int:
    return db.query(Transaction).filter(Transaction.date >= start, Transaction.date < end).count()


def categorize_step(db: Session, start: datetime, end: datetime) -> dict:
    """Étape 1 : dépenses du mois sans catégorie (mêmes filtres que l'audit, bornés au mois)."""

    def scoped(query):
        return query.filter(
            Transaction.category_id.is_(None),
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
        )

    base = scoped(db.query(Transaction))
    count = base.count()
    total = scoped(db.query(func.coalesce(func.sum(NET_AMOUNT), 0.0))).scalar()
    items = base.order_by(Transaction.amount.desc(), Transaction.id.asc()).limit(CATEGORIZE_LIMIT).all()
    return {"count": count, "total": round(float(total or 0.0), 2), "items": [_review_tx(t) for t in items]}


def top_expenses(db: Session, start: datetime, end: datetime) -> list[dict]:
    """Plus grosses dépenses nettes du mois (hors virements et investissement), à marquer exceptionnelles."""

    query = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
            Account.type.in_(["courant", "epargne"]),
            or_(Category.name.is_(None), Category.name.notin_(INVESTMENT_CATEGORIES)),
        )
    )
    tr_accounts = ticket_restaurant_account_ids(db)
    if tr_accounts:
        query = query.filter(Transaction.account_id.notin_(tr_accounts))
    rows = query.order_by(NET_AMOUNT.desc(), Transaction.id.asc()).limit(TOP_EXPENSES_LIMIT).all()
    return [_review_tx(t) for t in rows]


def month_fingerprint(db: Session, start: datetime, end: datetime) -> dict[str, dict[str, float]]:
    """Totaux nets du mois par devise de compte (entrées / sorties), sans conversion : insensibles aux taux de change."""

    rows = (
        db.query(Account.currency, Transaction.type, func.coalesce(func.sum(NET_AMOUNT), 0.0))
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.type.in_(["Entree", "Interets", "Sortie"]),
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Account.currency, Transaction.type)
        .all()
    )
    fingerprint: dict[str, dict[str, float]] = {}
    for currency, type_, total in rows:
        bucket = fingerprint.setdefault(currency, {"in": 0.0, "out": 0.0})
        bucket["out" if type_ == "Sortie" else "in"] += float(total)
    return {c: {k: round(v, 2) for k, v in b.items()} for c, b in sorted(fingerprint.items())}


# --- Revue d'un mois (routes /month-review) ------------------------------------------------------

def _accounts_step(db: Session, end: datetime) -> dict:
    """Étape 2 : un compte est « vérifié » s'il l'a été depuis la fin du mois (ou aujourd'hui si le mois n'est pas fini)."""
    now = utcnow_naive()
    reference = min(end, datetime(now.year, now.month, now.day))
    accounts = repo.active_accounts(db)
    items = [
        {
            "id": acc.id,
            "name": acc.name,
            "currency": acc.currency,
            "balance": round(account_balance(db, acc.id), 2),
            "last_verified_at": acc.last_verified_at,
            "verified_since_month_end": acc.last_verified_at >= reference,
        }
        for acc in accounts
    ]
    return {"unverified_count": sum(1 for i in items if not i["verified_since_month_end"]), "accounts": items}


async def _build_review(db: Session, year: int, month: int) -> tuple[dict, dict]:
    start, end = month_bounds(db, year, month)
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)

    budget = await compute_budget(month=month, year=year, account_id=None, db=db)
    previous = await compute_budget(month=prev_month, year=prev_year, account_id=None, db=db)
    alerts = await compute_budget_alerts(year=year, month=month, account_id=None, db=db)
    rates = await get_exchange_rates("EUR")

    categorize = categorize_step(db, start, end)
    accounts = _accounts_step(db, end)
    current = {
        "tx_count": tx_count(db, start, end),
        "income": round(float(budget["revenus_totaux"]), 2),
        "expenses": round(float(budget["depenses_reelles"]), 2),
        "unresolved_count": categorize["count"] + accounts["unverified_count"],
        "fingerprint": month_fingerprint(db, start, end),
    }

    closure = repo.get_closure(db, year, month)
    # Comparaison exacte des totaux par devise (aucune conversion, donc aucune dérive de taux) ;
    # une clôture sans empreinte (ancienne ligne) ne se compare que sur le nombre de transactions.
    modified = closure is not None and (
        current["tx_count"] != closure.tx_count
        or (closure.fingerprint is not None and json.loads(closure.fingerprint) != current["fingerprint"])
    )

    review = {
        "year": year,
        "month": month,
        "closed": closure is not None,
        "closure": ClosureRead.model_validate(closure) if closure else None,
        "modified_since_close": modified,
        "categorize": categorize,
        "accounts": accounts,
        "budget": {
            "income": current["income"],
            "real_expenses": current["expenses"],
            "savings": round(savings_basis(budget), 2),
            "savings_rate": budget["taux_epargne"],
            "burn_rate": budget["burn_rate"],
            **without_exceptional(budget, exceptional_expenses(db, start, end, rates)),
            "previous_real_expenses": previous["depenses_reelles"],
            "alerts": alerts,
            "top_expenses": top_expenses(db, start, end),
        },
    }
    return review, current


async def get_month_review(db: Session, year: int, month: int) -> dict:
    """État de la revue d'un mois : étapes 1 à 3 calculées, statut de clôture, indicateur de modification."""
    review, _ = await _build_review(db, year, month)
    return review


async def close_month(db: Session, payload: CloseRequest) -> dict:
    """Marque le mois comme revu et fige la photo des chiffres. Idempotent : re-clôturer remplace la photo."""
    _, current = await _build_review(db, payload.year, payload.month)
    closure = repo.get_closure(db, payload.year, payload.month)
    if closure is None:
        closure = MonthClosure(year=payload.year, month=payload.month)
        db.add(closure)
    closure.closed_at = utcnow_naive()
    closure.highlight = (payload.highlight or "").strip() or None
    closure.tx_count = current["tx_count"]
    closure.income = current["income"]
    closure.expenses = current["expenses"]
    closure.unresolved_count = current["unresolved_count"]
    closure.fingerprint = json.dumps(current["fingerprint"], sort_keys=True)
    db.commit()
    review, _ = await _build_review(db, payload.year, payload.month)
    return review


def reopen_month(db: Session, year: int, month: int) -> None:
    """Rouvre un mois (supprime sa clôture). Sans effet si le mois n'était pas clôturé."""
    repo.delete_closure(db, year, month)
    db.commit()


def list_closures(db: Session) -> list[MonthClosure]:
    return repo.list_closures(db)
