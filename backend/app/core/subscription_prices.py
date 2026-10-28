"""Détection des hausses de prix des abonnements et prélèvements réguliers.

Une série = les sorties d'un même compte rattachées à la même récurrence, sinon au même
marchand canonique, sinon au même libellé. Elle est retenue si ses échéances sont
régulières (mensuelle, trimestrielle ou annuelle) ; une hausse est signalée quand le dernier
prélèvement dépasse un montant précédent stable. Aucune écriture : simple lecture.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import median

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.merchant import Merchant
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction

# (écart médian min, max en jours, prélèvements par an, libellé)
CADENCES = (
    (25, 35, 12, "monthly"),
    (80, 100, 4, "quarterly"),
    (340, 390, 1, "yearly"),
)
LOOKBACK_DAYS = 800  # deux ans et plus : une hausse annuelle a besoin de l'échéance précédente
MIN_INCREASE = 0.10  # en devise du compte, sous ce seuil c'est un arrondi
MIN_INCREASE_PCT = 0.01
EPS = 0.005
# Une hausse reste signalée ~6 mois (un an pour un prélèvement annuel), puis devient le prix normal
RECENT_DAYS = 180


@dataclass
class PriceChange:
    key: str
    name: str
    account_id: int
    currency: str
    frequency: str
    old_amount: float
    new_amount: float
    changed_on: date
    per_year: int

    @property
    def delta(self) -> float:
        return round(self.new_amount - self.old_amount, 2)

    @property
    def delta_pct(self) -> float:
        return round(self.delta / self.old_amount * 100, 1) if self.old_amount else 0.0

    @property
    def annual_impact(self) -> float:
        return round(self.delta * self.per_year, 2)


def price_change_id(change: PriceChange) -> str:
    return f"subscription-price-{change.account_id}-{change.key}-{change.changed_on.isoformat()}"


def _cadence(dates: list[datetime]) -> tuple[int, str] | None:
    gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    if not gaps:
        return None
    gap = median(gaps)
    for low, high, per_year, label in CADENCES:
        if low <= gap <= high:
            return per_year, label
    return None


def detect_price_changes(db: Session, account_id: int | None = None, now: datetime | None = None) -> list[PriceChange]:
    now = now or datetime.now()
    query = (
        db.query(
            Transaction.account_id,
            Transaction.date,
            Transaction.amount,
            Transaction.merchant,
            Transaction.merchant_id,
            Transaction.recurring_transaction_id,
            Account.currency,
            Merchant.name.label("merchant_name"),
            RecurringTransaction.name.label("recurring_name"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .outerjoin(Merchant, Transaction.merchant_id == Merchant.id)
        .outerjoin(RecurringTransaction, Transaction.recurring_transaction_id == RecurringTransaction.id)
        .filter(
            Account.active.is_(True),
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.is_subscription_ignored.is_(False),
            Transaction.date >= now - timedelta(days=LOOKBACK_DAYS),
            Transaction.date <= now,
            (Category.name.is_(None)) | (Category.name.notin_(("Investissement", "Epargne"))),
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)

    series: dict[tuple, list] = defaultdict(list)
    for row in query.all():
        if row.recurring_transaction_id:
            key = ("r", row.recurring_transaction_id)
        elif row.merchant_id:
            key = ("m", row.merchant_id)
        else:
            key = ("l", (row.merchant or "").strip().lower())
        series[(row.account_id, *key)].append(row)

    changes: list[PriceChange] = []
    for (acc_id, kind, ident), rows in series.items():
        if len(rows) < 2:
            continue
        cadence = _cadence([r.date for r in rows])
        if cadence is None:
            continue
        per_year, frequency = cadence
        last = rows[-1]
        # Dernier prélèvement récent : une série arrêtée n'est plus un abonnement en cours
        if (now - last.date).days > 1.5 * 365 / per_year:
            continue
        # Nouveau tarif = dernière suite de montants identiques ; ancien = suite stable juste avant
        new = float(last.amount)
        start = len(rows) - 1
        while start > 0 and abs(float(rows[start - 1].amount) - new) <= EPS:
            start -= 1
        changed = rows[start]
        if (now - changed.date).days > max(RECENT_DAYS, 1.1 * 365 / per_year):
            continue
        needed = 1 if per_year == 1 else 2  # l'annuel n'a souvent qu'une échéance précédente
        reference = [float(r.amount) for r in rows[max(0, start - needed):start]]
        if len(reference) < needed:
            continue
        old = reference[-1]
        if any(abs(a - old) > EPS for a in reference):
            continue
        if new - old < MIN_INCREASE or new < old * (1 + MIN_INCREASE_PCT):
            continue
        name = last.recurring_name or last.merchant_name or last.merchant
        changes.append(PriceChange(
            key=f"{kind}{ident}" if kind != "l" else f"l{ident[:60]}",
            name=name,
            account_id=acc_id,
            currency=last.currency or "EUR",
            frequency=frequency,
            old_amount=round(old, 2),
            new_amount=round(new, 2),
            changed_on=changed.date.date(),
            per_year=per_year,
        ))
    changes.sort(key=lambda c: c.changed_on, reverse=True)
    return changes
