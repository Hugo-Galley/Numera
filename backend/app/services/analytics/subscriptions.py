"""Abonnements et charges fixes : récurrences, abonnements détectés, hausses de prix, total mensuel."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.domain.finance import get_recurring_occurrences, is_lapsed
from app.domain.subscription_prices import PriceChange, price_change_id
from app.domain.subscriptions import recurring_costs
from app.integrations.currency import get_exchange_rates
from app.repositories.analytics import subscriptions as repo
from app.repositories.analytics.common import ticket_restaurant_account_ids
from app.schemas.insight import SubscriptionIgnore, SubscriptionInsight, SubscriptionPriceChange, SubscriptionsResponse
from app.services.budget_period import period_bounds
from app.services.subscription_prices import detect_price_changes


async def compute_subscriptions(db: Session, account_id: int | None = None, include_other: bool = False) -> SubscriptionsResponse:
    """include_other : ajoute les récurrences qui ne sont pas des sorties (salaire, etc.),
    marquées par flow_type ; elles sont exclues des totaux.
    """
    rates = await get_exchange_rates("EUR")
    subscriptions = [_recurring_insight(db, rd, rates) for rd in repo.recurrings(db, account_id, include_other)]
    subscriptions += _potential_insights(db, account_id, subscriptions)
    outflows = [s for s in subscriptions if s.flow_type == "Sortie" and s.counts_in_total]
    return SubscriptionsResponse(
        subscriptions=subscriptions,
        total_monthly=round(sum(s.monthly_cost for s in outflows), 2),
        total_annual=round(sum(s.annual_cost for s in outflows), 2),
        price_changes=[price_change_read(c) for c in detect_price_changes(db, account_id=account_id)],
    )


def _recurring_insight(db: Session, rd, rates: dict) -> SubscriptionInsight:
    # Coût mensuel/annuel en EUR : le montant d'une récurrence est dans sa propre devise
    monthly_cost, annual_cost = recurring_costs(rd.amount, rd.frequency, rates.get(rd.currency or "EUR", 1.0) or 1.0)
    is_savings_flow = bool(rd.transfer_to_account_id) or (
        rd.category is not None and rd.category.name in ("Investissement", "Epargne")
    )
    last_tx = repo.last_occurrence(db, rd.id)
    # Prochaine échéance sur un peu plus d'un an : une récurrence annuelle a aussi sa prochaine date
    next_occs = get_recurring_occurrences(rd, datetime.now(), datetime.now() + timedelta(days=400))
    lapsed = bool(rd.is_active) and is_lapsed(rd.frequency, last_tx.date if last_tx else None, datetime.now())
    return SubscriptionInsight(
        name=rd.name,
        category_name=rd.category.name if rd.category else "Abonnement",
        amount=float(rd.amount),
        frequency=rd.frequency,
        monthly_cost=round(monthly_cost, 2),
        annual_cost=round(annual_cost, 2),
        last_occurrence=last_tx.date.isoformat() if last_tx else None,
        next_occurrence=next_occs[0].isoformat() if next_occs else None,
        is_recurring_entity=True,
        status=("lapsed" if lapsed else "active") if rd.is_active else "paused",
        logo=rd.logo,
        flow_type=rd.type,
        # Plus prélevée depuis deux périodes : affichée à part, hors des totaux
        counts_in_total=bool(rd.is_active) and not lapsed and not is_savings_flow,
    )


def _potential_insights(db: Session, account_id: int | None, known: list[SubscriptionInsight]) -> list[SubscriptionInsight]:
    """Abonnements probables : même marchand et même montant répétés sur 90 jours, hors récurrences connues."""
    found: list[SubscriptionInsight] = []
    for p in repo.potential_subscriptions(db, datetime.now() - timedelta(days=90), account_id):
        if any(s.name.lower() == p.merchant.lower() for s in known + found):
            continue
        monthly_cost = float(p.amount)
        found.append(SubscriptionInsight(
            name=p.merchant,
            category_name=p.category_name or "Abonnement",
            amount=float(p.amount),
            frequency="monthly (detected)",
            monthly_cost=round(monthly_cost, 2),
            annual_cost=round(monthly_cost * 12, 2),
            last_occurrence=p.last_date.isoformat(),
            next_occurrence=None,
            is_recurring_entity=False,
            status="potential"
        ))
    return found


def price_change_read(change: PriceChange) -> SubscriptionPriceChange:
    return SubscriptionPriceChange(
        id=price_change_id(change),
        name=change.name,
        account_id=change.account_id,
        currency=change.currency,
        frequency=change.frequency,
        old_amount=change.old_amount,
        new_amount=change.new_amount,
        delta=change.delta,
        delta_pct=change.delta_pct,
        annual_impact=change.annual_impact,
        changed_on=change.changed_on.isoformat(),
    )


def ignore_subscription_detection(db: Session, data: SubscriptionIgnore) -> dict:
    """Exclut de la détection toutes les transactions de ce marchand à ce montant."""
    repo.ignore_detection(db, data.merchant, data.amount)
    db.commit()
    return {"status": "ok"}


async def get_subscription_total_for_period(month: int, year: int, db: Session) -> float:
    """Total EUR des sorties de catégorie « Abonnement » du mois budgétaire."""
    start, end = period_bounds(db, year, month)
    rates = await get_exchange_rates("EUR")
    total_eur = 0.0
    for row in repo.subscription_category_rows(db, start, end, ticket_restaurant_account_ids(db)):
        total_eur += row.total / rates.get(row.currency, 1.0)
    return total_eur
