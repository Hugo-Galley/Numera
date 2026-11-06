"""Outils MCP analytics : projections, historique des KPI, flux d'argent et patrimoine."""

from typing import Any

from numera_mcp.api_client import api, handle_response
from numera_mcp.formatting import serialize


def get_kpi_history(months: int = 6) -> str:
    """Historique des KPIs financiers sur N mois (revenus, dépenses, épargne, etc.).

    Args:
        months: Nombre de mois d'historique (défaut 6)
    """
    try:
        resp = api.get("/analytics/kpi-history", params={"months_count": max(1, min(months, 24))})
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"📈 Historique KPI ({months} mois) :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_cashflow_projection(months: int = 3) -> str:
    """Projection de trésorerie sur les prochains mois.

    Args:
        months: Nombre de mois de projection (défaut 3)
    """
    try:
        resp = api.get("/analytics/cashflow-projection", params={"months": months})
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"🔮 Projection trésorerie :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_wealth_forecast(
    years: int = 10,
    extra_monthly: float = 0.0,
    monthly_savings: float | None = None,
    investment_return_pct: float | None = None,
    savings_return_pct: float | None = None,
) -> str:
    """Prévision simple du patrimoine : patrimoine actuel + épargne mensuelle moyenne des 12 derniers mois,
    rendement des investissements = XIRR constaté. Compare le rythme actuel à un effort d'épargne supplémentaire.

    Args:
        years: Horizon en années (défaut 10)
        extra_monthly: Épargne mensuelle supplémentaire hypothétique en € (défaut 0)
        monthly_savings: Remplace l'épargne mensuelle moyenne calculée (optionnel)
        investment_return_pct: Remplace le rendement constaté (XIRR) des comptes d'investissement (optionnel)
        savings_return_pct: Rendement annuel des autres comptes, 0 par défaut (optionnel)
    """
    try:
        params: dict = {"years": years, "extra_monthly": extra_monthly}
        if monthly_savings is not None:
            params["monthly_savings"] = monthly_savings
        if investment_return_pct is not None:
            params["investment_return_pct"] = investment_return_pct
        if savings_return_pct is not None:
            params["savings_return_pct"] = savings_return_pct
        resp = api.get("/analytics/wealth-forecast", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"🔭 Prévision de patrimoine ({years} ans) :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_fire_projection(
    withdrawal_rate_pct: float = 4.0,
    inflation_pct: float = 2.0,
    return_pct: float | None = None,
    monthly_savings: float | None = None,
    annual_expenses: float | None = None,
) -> str:
    """Indépendance financière : patrimoine cible = dépenses annuelles ÷ taux de retrait, années pour l'atteindre
    au rythme d'épargne réel (en euros d'aujourd'hui), et scénarios (+100/+250/+500 €/mois, dépenses −10 %).

    Args:
        withdrawal_rate_pct: Taux de retrait annuel (défaut 4, règle des 4 %)
        inflation_pct: Inflation annuelle retranchée du rendement (défaut 2)
        return_pct: Remplace le rendement nominal constaté (optionnel)
        monthly_savings: Remplace l'épargne mensuelle moyenne (optionnel)
        annual_expenses: Remplace les dépenses annuelles réelles (optionnel)
    """
    try:
        params: dict = {"withdrawal_rate_pct": withdrawal_rate_pct, "inflation_pct": inflation_pct}
        if return_pct is not None:
            params["return_pct"] = return_pct
        if monthly_savings is not None:
            params["monthly_savings"] = monthly_savings
        if annual_expenses is not None:
            params["annual_expenses"] = annual_expenses
        resp = api.get("/analytics/fire", params=params)
        error = handle_response(resp)
        if error:
            return error
        return f"🔥 Indépendance financière :\n\n{serialize(resp.json())}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_money_flow(
    month: int | None = None,
    year: int | None = None,
    account_id: int | None = None,
) -> str:
    """Flux d'argent détaillé : d'où vient l'argent et où il va.

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

        resp = api.get("/analytics/money-flow", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"💸 Flux d'argent :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_patrimoine_allocation() -> str:
    """Répartition complète du patrimoine global : courant, épargne, investissements, assurance-vie.

    Vue macro de tous les comptes actifs avec leur valeur actuelle, type et part du patrimoine.
    Complément idéal à get_diversity_scanner pour avoir une vue d'ensemble.
    """
    try:
        resp = api.get("/analytics/patrimoine-allocation")
        error = handle_response(resp)
        if error:
            return error
        return f"🏛️ Allocation du patrimoine :\n\n{serialize(resp.json())}"
    except Exception as e:
        return f"❌ Erreur : {e}"


TOOLS = [
    get_kpi_history,
    get_cashflow_projection,
    get_wealth_forecast,
    get_fire_projection,
    get_money_flow,
    get_patrimoine_allocation,
]


def register(mcp) -> None:
    for tool in TOOLS:
        mcp.tool()(tool)
