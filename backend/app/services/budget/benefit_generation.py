"""Entrées mensuelles des aides (prime d'activité, APL…) : provisoires, puis remplacées par le vrai versement.

Chaque mois, le jour de versement atteint, une `Entree` au montant attendu est créée sur le compte de
réception (`is_provisional`), sauf si le versement réel est déjà arrivé. Quand l'import apporte une entrée
dont le libellé contient le motif de l'aide, elle prend la place de l'entrée provisoire (montant réel,
soldes recalculés) : aucun doublon de revenu. Idempotent ; seul le mois en cours est généré.
"""
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.time import utcnow_naive
from app.domain import benefits as calc
from app.models.benefit import Benefit
from app.models.transaction import Transaction
from app.repositories.budget import benefits as repo
from app.services.budget.balances import recalculate_running_balances

logger = get_logger(__name__)

# Écart maximal entre l'entrée provisoire et le vrai versement qui la remplace
REPLACE_WINDOW_DAYS = calc.EARLY_DAYS


def _already_covered(db: Session, benefit: Benefit, expected: date) -> bool:
    """Versement du mois déjà reçu, ou entrée générée déjà posée (même remplacée)."""
    month_start = datetime.combine(expected.replace(day=1), time.min)
    month_end = datetime.combine(calc.add_months(expected.replace(day=1), 1), time.min)
    if repo.has_generated_in(db, benefit.id, month_start, month_end):
        return True
    since = datetime.combine(expected - timedelta(days=calc.EARLY_DAYS), time.min)
    return bool(repo.matching_entries(db, benefit, since))


def generate_benefit_transactions(db: Session, today: date | None = None) -> int:
    """Crée l'entrée provisoire du mois pour chaque aide à générer. Renvoie le nombre créé."""
    today = today or utcnow_naive().date()
    touched: set[int] = set()
    created = 0
    for benefit in repo.list_active(db):
        if not benefit.auto_generate or benefit.account_id is None:
            continue
        expected = calc.expected_this_month(today, benefit.payment_day)
        if today < expected or (benefit.start_date is not None and benefit.start_date > expected):
            continue
        if _already_covered(db, benefit, expected):
            continue
        when = datetime.combine(expected, time.min)
        db.add(Transaction(
            account_id=benefit.account_id, date=when, month_label=f"{expected.year}-{expected.month:02d}",
            type="Entree", merchant=benefit.name, amount=benefit.amount, original_amount=benefit.amount,
            currency=benefit.account.currency or "EUR", running_balance=0.0,
            note=f"Versement attendu ({benefit.organization}) : remplacé par le vrai versement à l'import",
            benefit_id=benefit.id, is_provisional=True,
        ))
        touched.add(benefit.account_id)
        created += 1
    if created:
        db.flush()
        for account_id in touched:
            recalculate_running_balances(db, account_id)
        db.commit()
        logger.info(f"Aides : {created} entrée(s) provisoire(s) générée(s)")
    return created


def reconcile_provisional(db: Session) -> int:
    """Remplace chaque entrée provisoire par le vrai versement correspondant. Renvoie le nombre remplacé."""
    provisionals = repo.provisional_entries(db)
    if not provisionals:
        return 0
    pairs: list[tuple[float, int, Transaction, Transaction]] = []
    for prov in provisionals:
        benefit = prov.benefit
        if benefit is None:
            continue
        since = prov.date - timedelta(days=REPLACE_WINDOW_DAYS)
        pairs.extend(
            (abs(real.amount - prov.amount), abs((real.date - prov.date).days), prov, real)
            for real in repo.matching_entries(db, benefit, since)
            if real.account_id == prov.account_id and abs((real.date - prov.date).days) <= REPLACE_WINDOW_DAYS
        )
    # Appariement 1 pour 1, du plus proche au plus éloigné : un versement ne remplace qu'une entrée
    used_prov: set[int] = set()
    used_real: set[int] = set()
    touched: set[int] = set()
    replaced = 0
    for _gap, _days, prov, real in sorted(pairs, key=lambda p: (p[0], p[1], p[2].id, p[3].id)):
        if prov.id in used_prov or real.id in used_real:
            continue
        used_prov.add(prov.id)
        used_real.add(real.id)
        real.benefit_id = prov.benefit_id  # hérite du logo
        touched.add(prov.account_id)
        db.delete(prov)
        replaced += 1
    if replaced:
        db.flush()
        for account_id in touched:
            recalculate_running_balances(db, account_id)
        db.commit()
        logger.info(f"Aides : {replaced} entrée(s) provisoire(s) remplacée(s) par le vrai versement")
    return replaced
