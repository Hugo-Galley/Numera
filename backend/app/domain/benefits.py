"""Aides perçues : calculs purs (date de versement attendue, statut du mois, déclaration, rattachement)."""
import calendar
from collections.abc import Iterable, Sequence
from datetime import date, timedelta

# Un versement peut arriver avant le jour habituel (week-end, jour férié)
EARLY_DAYS = 10
# Délai après le jour habituel avant de signaler un versement manquant
LATE_DAYS = 5
# Écart toléré entre le montant reçu et le montant attendu
AMOUNT_TOLERANCE_PCT = 0.05
AMOUNT_TOLERANCE_EUR = 1.0


def payment_date(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def add_months(d: date, months: int) -> date:
    index = d.month - 1 + months
    year, month = d.year + index // 12, index % 12 + 1
    return payment_date(year, month, d.day)


def expected_this_month(today: date, payment_day: int) -> date:
    return payment_date(today.year, today.month, payment_day)


def month_status(
    today: date, payment_day: int, payment_dates: Iterable[date], start: date | None = None
) -> tuple[str, date]:
    """(statut, date de versement attendue) du mois en cours.

    `received` : un versement est arrivé depuis `attendu − EARLY_DAYS` ; `late` : rien `LATE_DAYS` jours
    après la date attendue ; `pending` sinon. Une aide qui démarre après la date attendue n'est pas en retard.
    """
    expected = expected_this_month(today, payment_day)
    if any(d >= expected - timedelta(days=EARLY_DAYS) for d in payment_dates):
        return "received", expected
    if start is not None and start > expected:
        return "pending", expected
    if today > expected + timedelta(days=LATE_DAYS):
        return "late", expected
    return "pending", expected


def next_payment_date(today: date, payment_day: int, status: str) -> date:
    expected = expected_this_month(today, payment_day)
    if status == "received" or today > expected:
        nxt = add_months(date(today.year, today.month, 1), 1)
        return payment_date(nxt.year, nxt.month, payment_day)
    return expected


def advance_declaration(current: date, interval_months: int, today: date) -> date:
    """Échéance suivante après une déclaration faite : au moins un intervalle, et toujours après aujourd'hui."""
    # Toujours compté depuis `current` : enchaîner les ajouts ferait glisser le 31 vers le 30
    k = 1
    while add_months(current, k * interval_months) <= today:
        k += 1
    return add_months(current, k * interval_months)


def amount_changed(expected: float, received: float) -> bool:
    gap = abs(received - expected)
    return gap > AMOUNT_TOLERANCE_EUR and gap > expected * AMOUNT_TOLERANCE_PCT


def assign(candidates: dict[int, Sequence[int]], amounts: dict[int, float], expected: dict[int, float]) -> dict[int, int]:
    """Rattache chaque versement (id → aides candidates) à une seule aide : celle au montant attendu le plus proche."""
    return {
        tx_id: min(benefit_ids, key=lambda b: (abs(amounts[tx_id] - expected[b]), b))
        for tx_id, benefit_ids in candidates.items()
        if benefit_ids
    }
