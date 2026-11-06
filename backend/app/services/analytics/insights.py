"""Insights du mois : score de santé financière et anomalies (abonnements, grosses dépenses, catégories)."""
from sqlalchemy.orm import Session

from app.core.i18n import tr
from app.domain.insights import category_anomalies, eur, health_score
from app.domain.transactions import net_amount
from app.integrations.currency import get_exchange_rates
from app.repositories.analytics import insights as repo
from app.repositories.analytics.common import ticket_restaurant_account_ids
from app.schemas.insight import Insight, IntelligentInsights
from app.services.analytics.budget import compute_budget, compute_resilience
from app.services.analytics.metrics import compute_expenses_by_category
from app.services.analytics.metrics.categories import UNCATEGORIZED
from app.services.analytics.subscriptions import get_subscription_total_for_period
from app.services.budget.budget_period import period_bounds


def _previous(month: int, year: int, back: int = 1) -> tuple[int, int]:
    m_idx, y_idx = month - back, year
    if m_idx <= 0:
        m_idx += 12
        y_idx -= 1
    return m_idx, y_idx


async def compute_insights(db: Session, month: int, year: int, account_id: int | None = None) -> IntelligentInsights:
    rates = await get_exchange_rates("EUR")
    start_month, end_month = period_bounds(db, year, month)
    budget_data = await compute_budget(month=month, year=year, account_id=account_id, db=db)
    if account_id:
        burn_rate, epargne_total = budget_data["burn_rate"], budget_data["epargne_total"]
        runway_months = (epargne_total / burn_rate / 30.5) if (burn_rate > 0 and epargne_total > 0) else 0.0
    else:
        # Vue globale : même indice que la page Épargne (moyenne des derniers mois complets)
        runway_months = (await compute_resilience(db, year, month))["months"] or 0.0
    score = health_score(budget_data, runway_months)

    insights = await _subscription_increase(db, month, year)
    insights += _large_expenses(db, start_month, end_month, account_id, budget_data["revenus_totaux"], rates)
    insights += await _category_anomalies(db, month, year, account_id)
    insights += _positive_insights(budget_data["taux_epargne"], runway_months, month, year)

    # Un insight écarté l'est pour son mois et son objet (la clé en porte les deux), pas pour son titre générique
    dismissed = repo.dismissed_keys(db)
    return IntelligentInsights(health_score=score, insights=[i for i in insights if i.key not in dismissed])


async def _subscription_increase(db: Session, month: int, year: int) -> list[Insight]:
    prev_month, prev_year = _previous(month, year)
    current = await get_subscription_total_for_period(month=month, year=year, db=db)
    previous = await get_subscription_total_for_period(month=prev_month, year=prev_year, db=db)
    if current <= previous:
        return []
    diff = current - previous
    return [Insight(
        type="anomaly",
        key=f"subs-increase-{year}-{month:02d}",
        title=tr("insights.subscription_increase.title"),
        description=tr("insights.subscription_increase.description", amount=eur(diff)),
        severity="medium",
        value=diff
    )]


def _large_expenses(db: Session, start, end, account_id: int | None, revenus: float, rates: dict) -> list[Insight]:
    """Sorties isolées au-delà de 10 % des revenus (au moins 500 €), hors épargne/investissement."""
    tr_accounts = set() if account_id else ticket_restaurant_account_ids(db)
    insights = []
    for tx, curr in repo.month_expenses(db, start, end, account_id, tr_accounts):
        val_eur = net_amount(tx) / rates.get(curr, 1.0)
        if tx.category and tx.category.name in ("Investissement", "Epargne"):
            continue
        if val_eur > max(revenus * 0.1, 500.0):
            insights.append(Insight(
                type="anomaly",
                key=f"large-expense-{tx.id}",
                title=tr("insights.large_expense.title"),
                description=tr("insights.large_expense.description", merchant=tx.merchant, amount=eur(val_eur)),
                severity="high" if val_eur > revenus * 0.3 else "medium",
                value=val_eur
            ))
    return insights


async def _category_anomalies(db: Session, month: int, year: int, account_id: int | None) -> list[Insight]:
    """Catégories à plus de deux fois leur moyenne des trois mois précédents."""
    current = await compute_expenses_by_category(month=month, year=year, account_id=account_id, db=db)
    current_totals = {item["category"]["id"]: item["total"] for item in current["items"]}
    histories: dict = {}
    for back in range(1, 4):
        m_idx, y_idx = _previous(month, year, back)
        hist = await compute_expenses_by_category(month=m_idx, year=y_idx, account_id=account_id, db=db)
        for item in hist["items"]:
            histories.setdefault(item["category"]["id"], []).append(item["total"])
    insights = []
    for cat_id, current_total, avg in category_anomalies(current_totals, histories):
        # « Sans catégorie » a un id None : pas de ligne en base
        cat_obj = repo.get_category(db, cat_id) if cat_id is not None else UNCATEGORIZED
        insights.append(Insight(
            type="anomaly",
            key=f"category-anomaly-{year}-{month:02d}-{cat_id}",
            title=tr("insights.category_alert.title", category=cat_obj.name),
            description=tr("insights.category_alert.description", category=cat_obj.name, current=eur(current_total), average=eur(avg)),
            severity="medium",
            value=current_total,
            category_id=cat_obj.id,
        ))
    return insights


def _positive_insights(savings_rate: float, runway_months: float, month: int, year: int) -> list[Insight]:
    insights = []
    if savings_rate > 30:
        insights.append(Insight(
            type="positive",
            key=f"high-savings-rate-{year}-{month:02d}",
            title=tr("insights.high_savings.title"),
            description=tr("insights.high_savings.description"),
            severity="low",
            value=savings_rate,
            unit="%",
        ))
    if runway_months > 12:
        insights.append(Insight(
            type="positive",
            key=f"long-runway-{year}-{month:02d}",
            title=tr("insights.long_runway.title"),
            description=tr("insights.long_runway.description"),
            severity="low",
            value=runway_months,
            unit="mois",
        ))
    return insights


def dismiss_insight(db: Session, key: str) -> dict:
    if not repo.is_dismissed(db, key):
        repo.add_dismissed(db, key)
        db.commit()
    return {"status": "success"}
