"""Détection des hausses de prix des abonnements et prélèvements réguliers.

Une série = les sorties d'un même compte rattachées à la même récurrence, sinon au même
marchand canonique, sinon au même libellé. Elle est retenue si ses échéances sont
régulières (mensuelle, trimestrielle ou annuelle) ; une hausse est signalée quand le dernier
prélèvement dépasse un montant précédent stable. Aucune écriture : simple lecture.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.time import now_local
from app.domain.subscription_prices import LOOKBACK_DAYS, PriceChange, series_change
from app.repositories.budget import subscription_prices as repo


def detect_price_changes(db: Session, account_id: int | None = None, now: datetime | None = None) -> list[PriceChange]:
    now = now or now_local()
    rows = repo.series_rows(db, now - timedelta(days=LOOKBACK_DAYS), now, account_id)

    series: dict[tuple[Any, ...], list[Any]] = defaultdict(list)
    for row in rows:
        if row.recurring_transaction_id:
            key = ("r", row.recurring_transaction_id)
        elif row.merchant_id:
            key = ("m", row.merchant_id)
        else:
            key = ("l", (row.merchant or "").strip().lower())
        series[(row.account_id, *key)].append(row)

    changes: list[PriceChange] = []
    for (acc_id, kind, ident), rows in series.items():
        change = series_change(rows, now)
        if change is None:
            continue
        last = rows[-1]
        name = last.recurring_name or last.merchant_name or last.merchant
        changes.append(PriceChange(
            key=f"{kind}{ident}" if kind != "l" else f"l{ident[:60]}",
            name=name,
            account_id=acc_id,
            currency=last.currency or "EUR",
            frequency=change.frequency,
            old_amount=change.old_amount,
            new_amount=change.new_amount,
            changed_on=change.changed_on,
            per_year=change.per_year,
        ))
    changes.sort(key=lambda c: c.changed_on, reverse=True)
    return changes
