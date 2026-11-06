"""Outils MCP du domaine analytics (budget, KPI, projections, flux, patrimoine)."""

from datetime import datetime
from typing import Any

from numera_mcp.api_client import api, handle_response
from numera_mcp.budget_period import current_budget_month
from numera_mcp.formatting import serialize


def get_budget_summary(month: int | None = None, year: int | None = None, account_id: int | None = None) -> str:
    """Résumé budget complet : revenus, dépenses par catégorie, soldes des comptes.

    Args:
        month: Mois (1-12, optionnel, défaut: mois budgétaire en cours)
        year: Année (optionnel, défaut: année du mois en cours)
        account_id: Filtrer par compte (optionnel)
    """
    try:
        # Sans mois ni année, l'API renvoie le cumul depuis le début : on demande le mois en cours
        if month is None and year is None:
            year, month = current_budget_month()
        params: dict[str, Any] = {}
        if month is not None:
            params["month"] = month
        if year is not None:
            params["year"] = year
        if account_id is not None:
            params["account_id"] = account_id

        resp = api.get("/analytics/budget", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"📊 Résumé budget :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_expenses_by_category(
    month: int | None = None,
    year: int | None = None,
    account_id: int | None = None,
) -> str:
    """Répartition des dépenses par catégorie.

    Args:
        month: Mois (1-12, optionnel)
        year: Année (optionnel)
        account_id: Filtrer par compte (optionnel)
    """
    try:
        params: dict[str, Any] = {}
        if month is not None:
            params["month"] = month
        if year is not None:
            params["year"] = year
        if account_id is not None:
            params["account_id"] = account_id

        resp = api.get("/analytics/expenses-by-category", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"💸 Dépenses par catégorie :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_top_merchants(
    month: int | None = None,
    year: int | None = None,
    account_id: int | None = None,
    limit: int = 10,
) -> str:
    """Top marchands par montant dépensé.

    Args:
        month: Mois (1-12, optionnel)
        year: Année (optionnel)
        account_id: Filtrer par compte (optionnel)
        limit: Nombre de marchands (défaut 10)
    """
    try:
        params: dict[str, Any] = {"limit": min(limit, 50)}
        if month is not None:
            params["month"] = month
        if year is not None:
            params["year"] = year
        if account_id is not None:
            params["account_id"] = account_id

        resp = api.get("/analytics/top-merchants", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"🏪 Top marchands :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_subscriptions() -> str:
    """Analyse complète des abonnements détectés : actifs, montants, insights."""
    try:
        resp = api.get("/analytics/subscriptions")
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"📋 Analyse des abonnements :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_budget_alerts(month: int | None = None, year: int | None = None) -> str:
    """Alertes budgétaires : catégories proches ou dépassant les limites.

    Args:
        month: Mois (1-12, défaut : mois budgétaire en cours)
        year: Année (défaut : année du mois en cours)
    """
    try:
        current_year, current_month = current_budget_month()
        params = {"month": month or current_month, "year": year or current_year}
        resp = api.get("/analytics/budget-alerts", params=params)
        error = handle_response(resp)
        if error:
            return error
        alerts = resp.json()
        if not alerts:
            return "✅ Aucune alerte budgétaire ! Tout est sous contrôle."

        lines = ["⚠️ Alertes budgétaires :\n"]
        for alert in alerts:
            name = alert.get("category_name", "?")
            monthly_ratio = alert.get("monthly_ratio")
            monthly_spent = alert.get("monthly_spent", 0)
            monthly_limit = alert.get("monthly_limit")

            if monthly_ratio and monthly_ratio >= 1.0:
                lines.append(f"  🔴 {name} : {monthly_spent:.2f}€ / {monthly_limit:.2f}€ ({monthly_ratio*100:.0f}%)")
            elif monthly_ratio and monthly_ratio >= 0.8:
                lines.append(f"  🟠 {name} : {monthly_spent:.2f}€ / {monthly_limit:.2f}€ ({monthly_ratio*100:.0f}%)")
            else:
                lines.append(f"  🟢 {name} : {monthly_spent:.2f}€ / {monthly_limit:.2f}€")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_insights(month: int | None = None, year: int | None = None) -> str:
    """Insights intelligents : score de santé financière, tendances, recommandations.

    Args:
        month: Mois (1-12, défaut : mois budgétaire en cours)
        year: Année (défaut : année du mois en cours)
    """
    try:
        current_year, current_month = current_budget_month()
        params = {"month": month or current_month, "year": year or current_year}
        resp = api.get("/analytics/insights", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"🧠 Insights financiers :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_monthly_report(month: int | None = None, year: int | None = None) -> str:
    """Rapport mensuel complet avec comparaison au mois précédent.

    Args:
        month: Mois (1-12, optionnel, défaut: mois budgétaire en cours)
        year: Année (optionnel, défaut: année du mois en cours)
    """
    try:
        # L'API exige mois et année
        current_year, current_month = current_budget_month()
        params: dict[str, Any] = {"month": month or current_month, "year": year or current_year}

        resp = api.get("/analytics/monthly-report", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"📊 Rapport mensuel :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_budget_period(month: int | None = None, year: int | None = None) -> str:
    """Découpage des mois : mode (mois de paie ou mois civil), mois en cours et fenêtre de dates.

    En mode « salary », chaque salaire reçu ouvre un mois qui porte le nom du mois qu'il finance
    (salaire du 25 août = septembre) ; tous les outils mensuels lisent ce découpage.

    Args:
        month: Mois (1-12, défaut : mois en cours)
        year: Année (défaut : année du mois en cours)
    """
    try:
        params = {k: v for k, v in {"month": month, "year": year}.items() if v is not None}
        resp = api.get("/analytics/budget-period", params=params)
        error = handle_response(resp)
        if error:
            return error
        return f"🗓️ Découpage des mois :\n\n{serialize(resp.json())}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_resilience(month: int | None = None, year: int | None = None) -> str:
    """Mois d'autonomie : épargne liquide ÷ dépenses réelles moyennes des 6 derniers mois complets.

    Args:
        month: Mois de référence (1-12, défaut : mois en cours)
        year: Année de référence (défaut : année en cours)
    """
    try:
        current_year, current_month = current_budget_month()
        params = {"month": month or current_month, "year": year or current_year}
        resp = api.get("/analytics/resilience", params=params)
        error = handle_response(resp)
        if error:
            return error
        return f"🛟 Résilience :\n\n{serialize(resp.json())}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_wrapped(year: int | None = None) -> str:
    """Bilan annuel : revenus, dépenses réelles, taux d'épargne, plus gros postes et marchands,
    plus grosse dépense, évolution du patrimoine, abonnements nouveaux/arrêtés, comparaison à N-1.

    L'année en cours est arrêtée au mois courant et comparée à la même période de N-1.

    Args:
        year: Année (optionnel, défaut: année en cours)
    """
    try:
        resp = api.get("/analytics/wrapped", params={"year": year if year is not None else datetime.now().year})
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"🎁 Bilan annuel :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


TOOLS = [
    get_budget_summary,
    get_expenses_by_category,
    get_top_merchants,
    get_subscriptions,
    get_budget_alerts,
    get_insights,
    get_monthly_report,
    get_budget_period,
    get_resilience,
    get_wrapped,
]


def register(mcp) -> None:
    for tool in TOOLS:
        mcp.tool()(tool)
