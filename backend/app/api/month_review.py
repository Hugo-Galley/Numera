import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.services.accounts import account_balance
from app.api.analytics.budget import budget_alerts, budget_analytics
from app.api.deps import get_db
from app.core.currency import get_exchange_rates
from app.core.month_review import (
    categorize_step,
    exceptional_expenses,
    month_bounds,
    month_fingerprint,
    savings_basis,
    top_expenses,
    tx_count,
    without_exceptional,
)
from app.core.time import utcnow_naive
from app.models.account import Account
from app.models.month_closure import MonthClosure
from app.schemas.month_review import CloseRequest, ClosureRead, MonthReviewRead

router = APIRouter(prefix="/month-review", tags=["month-review"])


def _accounts_step(db: Session, end: datetime) -> dict:
    """Étape 2 : un compte est « vérifié » s'il l'a été depuis la fin du mois (ou aujourd'hui si le mois n'est pas fini)."""
    now = utcnow_naive()
    reference = min(end, datetime(now.year, now.month, now.day))
    accounts = db.query(Account).filter(Account.active.is_(True)).order_by(Account.id.asc()).all()
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

    budget = await budget_analytics(month=month, year=year, account_id=None, db=db)
    previous = await budget_analytics(month=prev_month, year=prev_year, account_id=None, db=db)
    alerts = await budget_alerts(year=year, month=month, account_id=None, db=db)
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

    closure = db.query(MonthClosure).filter(MonthClosure.year == year, MonthClosure.month == month).first()
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


@router.get("", response_model=MonthReviewRead)
async def get_month_review(
    year: int = Query(ge=2000, le=2200),
    month: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
):
    """État de la revue d'un mois : étapes 1 à 3 calculées, statut de clôture, indicateur de modification."""
    review, _ = await _build_review(db, year, month)
    return review


@router.post("/close", response_model=MonthReviewRead)
async def close_month(payload: CloseRequest, db: Session = Depends(get_db)):
    """Marque le mois comme revu et fige la photo des chiffres. Idempotent : re-clôturer remplace la photo."""
    _, current = await _build_review(db, payload.year, payload.month)
    closure = (
        db.query(MonthClosure)
        .filter(MonthClosure.year == payload.year, MonthClosure.month == payload.month)
        .first()
    )
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


@router.delete("", status_code=204)
def reopen_month(
    year: int = Query(ge=2000, le=2200),
    month: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Rouvre un mois (supprime sa clôture). Sans effet si le mois n'était pas clôturé."""
    db.query(MonthClosure).filter(MonthClosure.year == year, MonthClosure.month == month).delete()
    db.commit()


@router.get("/closures", response_model=list[ClosureRead])
def list_closures(db: Session = Depends(get_db)):
    return db.query(MonthClosure).order_by(MonthClosure.year.desc(), MonthClosure.month.desc()).all()
