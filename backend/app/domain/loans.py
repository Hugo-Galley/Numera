"""Crédits : échéancier à mensualité constante, capital restant dû, remboursements anticipés.

Fonctions pures (aucune session) ; `terms_of` lit un prêt déjà chargé. `loan_remaining` (requête) : `services/loans.py`.
- Mensualité hors assurance : `m = P·r / (1 − (1+r)^−n)`, `r = taux annuel / 12` ; taux nul → `P / n`.
- Échéance n à `start_date + (n − 1) mois` (jour borné à la fin du mois), arrondie au centime par ligne ;
  la dernière ligne solde le capital restant.
- Un remboursement anticipé daté `d` s'applique après la dernière échéance de date ≤ `d` (après la première
  si `d` la précède) ; `reduce_duration` garde la mensualité, `reduce_payment` la recalcule sur la durée restante.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.models.loan import Loan

PrepaymentMode = Literal["reduce_duration", "reduce_payment"]


@dataclass(frozen=True)
class LoanTerms:
    principal: float
    annual_rate_pct: float
    duration_months: int
    start_date: date
    insurance_monthly: float = 0.0


@dataclass(frozen=True)
class Prepayment:
    date: date
    amount: float
    mode: PrepaymentMode


@dataclass(frozen=True)
class ScheduleRow:
    n: int
    date: date
    payment: float  # intérêts + capital, hors assurance
    interest: float
    principal: float
    insurance: float
    remaining: float  # après l'échéance et les remboursements anticipés de la période
    prepayment: float = 0.0


def add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year, month = start.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def monthly_payment(principal: float, annual_rate_pct: float, months: int) -> float:
    if months <= 0:
        return round(principal, 2)
    r = annual_rate_pct / 1200.0
    if r == 0:
        return round(principal / months, 2)
    return round(principal * r / (1 - (1 + r) ** -months), 2)


def _window(prepayments: list[Prepayment], row_date: date, next_date: date, first: bool) -> list[Prepayment]:
    """Remboursements anticipés appliqués après l'échéance `row_date`."""
    return [p for p in prepayments if (first or p.date >= row_date) and p.date < next_date]


def build_schedule(terms: LoanTerms, prepayments: list[Prepayment] | None = None) -> list[ScheduleRow]:
    prepayments = sorted(prepayments or [], key=lambda p: p.date)
    r = terms.annual_rate_pct / 1200.0
    remaining = round(terms.principal, 2)
    payment = monthly_payment(remaining, terms.annual_rate_pct, terms.duration_months)
    rows: list[ScheduleRow] = []
    n = 0
    while remaining > 0.004 and n < terms.duration_months:
        n += 1
        row_date = add_months(terms.start_date, n - 1)
        interest = round(remaining * r, 2)
        principal_part = round(payment - interest, 2)
        if n == terms.duration_months or principal_part >= remaining:
            principal_part = remaining
        remaining = round(remaining - principal_part, 2)

        extra = 0.0
        for p in _window(prepayments, row_date, add_months(terms.start_date, n), n == 1):
            applied = round(min(p.amount, remaining), 2)
            if applied <= 0:
                continue
            extra += applied
            remaining = round(remaining - applied, 2)
            if p.mode == "reduce_payment" and remaining > 0:
                payment = monthly_payment(remaining, terms.annual_rate_pct, terms.duration_months - n)

        rows.append(ScheduleRow(
            n=n, date=row_date, payment=round(interest + principal_part, 2), interest=interest,
            principal=principal_part, insurance=round(terms.insurance_monthly, 2), remaining=remaining,
            prepayment=round(extra, 2),
        ))
    return rows


def remaining_principal(terms: LoanTerms, prepayments: list[Prepayment], at: date) -> float:
    """Capital restant dû au soir du jour `at`."""
    rows = build_schedule(terms, prepayments)
    past = [row for row in rows if row.date <= at]
    if not past:
        early = sum(p.amount for p in prepayments if p.date <= at)
        return round(max(terms.principal - early, 0.0), 2)
    row = past[-1]
    # Remboursements anticipés de la période pas encore survenus à la date `at`
    pending = sum(
        p.amount for p in _window(prepayments, row.date, add_months(terms.start_date, row.n), row.n == 1) if p.date > at
    )
    return round(row.remaining + min(pending, row.prepayment), 2)


def simulate_prepayment(
    terms: LoanTerms, prepayments: list[Prepayment], amount: float, at: date, mode: PrepaymentMode
) -> dict:
    before = build_schedule(terms, prepayments)
    after = build_schedule(terms, [*prepayments, Prepayment(at, amount, mode)])
    interest_before = round(sum(row.interest for row in before), 2)
    interest_after = round(sum(row.interest for row in after), 2)
    crd = remaining_principal(terms, prepayments, at)
    effective = min(amount, crd)
    following = next((row for row in after if row.date > at), None)
    return {
        "interest_saved": round(interest_before - interest_after, 2),
        "total_interest_before": interest_before,
        "total_interest_after": interest_after,
        "new_end_date": after[-1].date if after else at,
        "months_saved": len(before) - len(after),
        "new_payment": following.payment if following else 0.0,
        # Plafond légal des indemnités (crédit immobilier) : min(6 mois d'intérêts sur la somme, 3 % du CRD)
        "max_penalty": round(min(effective * terms.annual_rate_pct / 1200.0 * 6, 0.03 * crd), 2),
    }


def terms_of(loan: "Loan") -> tuple[LoanTerms, list[Prepayment]]:
    terms = LoanTerms(
        principal=loan.principal, annual_rate_pct=loan.annual_rate_pct, duration_months=loan.duration_months,
        start_date=loan.start_date, insurance_monthly=loan.insurance_monthly or 0.0,
    )
    return terms, [Prepayment(p.date, p.amount, p.mode) for p in loan.prepayments]  # type: ignore[arg-type]
