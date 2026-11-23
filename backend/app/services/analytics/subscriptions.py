"""Abonnements et charges fixes : récurrences, abonnements détectés, hausses de prix, total mensuel."""
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.time import now_local
from app.domain.finance import get_recurring_occurrences, is_lapsed
from app.domain.subscription_prices import PriceChange, price_change_id
from app.domain.subscriptions import (
    RecurringLine,
    counted_in_kind_total,
    effective_essential,
    recurring_costs,
    reste_a_vivre,
    subscription_kind,
)
from app.integrations.currency import get_exchange_rates
from app.models.recurring_transaction import RecurringTransaction
from app.repositories.analytics import subscriptions as repo
from app.repositories.analytics.common import ticket_restaurant_account_ids
from app.schemas.insight import (
    CostTotals,
    ResteAVivreResponse,
    SubscriptionIgnore,
    SubscriptionInsight,
    SubscriptionPriceChange,
    SubscriptionsResponse,
)
from app.services.budget.budget_period import period_bounds
from app.services.budget.subscription_prices import detect_price_changes


async def compute_subscriptions(db: Session, account_id: int | None = None, include_other: bool = False) -> SubscriptionsResponse:
    """include_other : ajoute les récurrences qui ne sont pas des sorties (salaire, etc.),
    marquées par flow_type ; elles sont exclues des totaux.
    """
    rates = await get_exchange_rates("EUR")
    subscriptions = [_recurring_insight(db, rd, rates) for rd in repo.recurrings(db, account_id, include_other)]
    subscriptions += _potential_insights(db, account_id, subscriptions)
    for s in subscriptions:
        s.in_kind_total = counted_in_kind_total(s.kind, s.status, s.counts_in_total, s.is_recurring_entity)
    totals_by_kind = {
        kind: _cost_totals([s for s in subscriptions if s.kind == kind and s.in_kind_total])
        for kind in ("subscriptions", "investments", "other")
    }
    charges = [s for s in subscriptions if s.kind == "subscriptions" and s.in_kind_total]
    totals_by_essential = {
        key: _cost_totals([s for s in charges if s.is_essential is essential])
        for key, essential in (("essential", True), ("non_essential", False))
    }
    # Source unique du coût des abonnements (tableau de bord et Échéances) : récurrences confirmées de
    # l'onglet abonnements ; les abonnements détectés (`potential`) sont listés mais jamais comptés.
    total = totals_by_kind["subscriptions"]
    return SubscriptionsResponse(
        subscriptions=subscriptions,
        total_monthly=total.monthly,
        total_annual=total.annual,
        totals_by_kind=totals_by_kind,
        totals_by_essential=totals_by_essential,
        price_changes=[price_change_read(c) for c in detect_price_changes(db, account_id=account_id)],
    )


def _cost_totals(items: list[SubscriptionInsight]) -> CostTotals:
    return CostTotals(monthly=round(sum(s.monthly_cost for s in items), 2), annual=round(sum(s.annual_cost for s in items), 2))


async def compute_reste_a_vivre(db: Session) -> ResteAVivreResponse:
    """Reste à vivre mensuel : mêmes récurrences et mêmes règles d'inclusion que la page des abonnements."""
    insights = (await compute_subscriptions(db, include_other=True)).subscriptions
    result = reste_a_vivre([
        RecurringLine(s.flow_type, s.kind, s.in_kind_total, s.is_essential, s.monthly_cost) for s in insights
    ])
    return ResteAVivreResponse(**vars(result))


def _recurring_insight(db: Session, rd: RecurringTransaction, rates: dict[str, Any]) -> SubscriptionInsight:
    # Coût mensuel/annuel en EUR : le montant d'une récurrence est dans sa propre devise
    monthly_cost, annual_cost = recurring_costs(rd.amount, rd.frequency, rates.get(rd.currency or "EUR", 1.0) or 1.0)
    is_savings_flow = bool(rd.transfer_to_account_id) or (
        rd.category is not None and rd.category.name in ("Investissement", "Epargne")
    )
    last_tx = repo.last_occurrence(db, rd.id)
    # Prochaine échéance sur un peu plus d'un an : une récurrence annuelle a aussi sa prochaine date
    next_occs = get_recurring_occurrences(rd, now_local(), now_local() + timedelta(days=400))
    lapsed = bool(rd.is_active) and is_lapsed(rd.frequency, last_tx.date if last_tx else None, now_local())
    is_essential, essential_source = effective_essential(rd.is_essential, rd.category.name if rd.category else None)
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
        kind=subscription_kind(rd.category.name if rd.category else None, rd.type, bool(rd.transfer_to_account_id)),
        recurring_id=rd.id,
        is_essential=is_essential,
        is_essential_source=essential_source,
    )


def _potential_insights(db: Session, account_id: int | None, known: list[SubscriptionInsight]) -> list[SubscriptionInsight]:
    """Abonnements probables : même marchand et même montant répétés sur 90 jours, hors récurrences connues."""
    found: list[SubscriptionInsight] = []
    for p in repo.potential_subscriptions(db, now_local() - timedelta(days=90), account_id):
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
            status="potential",
            is_essential=effective_essential(None, p.category_name)[0],
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


def ignore_subscription_detection(db: Session, data: SubscriptionIgnore) -> dict[str, Any]:
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
