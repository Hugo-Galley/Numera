"""Mois budgétaire courant, partagé par les outils budget et analytics."""

from datetime import date

from numera_mcp.api_client import api
from numera_mcp.config import logger


def current_budget_month() -> tuple[int, int]:
    """(année, mois) du mois budgétaire en cours ; mois civil si l'API ne répond pas."""
    try:
        resp = api.get("/analytics/budget-period")
        if resp.status_code == 200:
            current = resp.json()["current"]
            return current["year"], current["month"]
    except Exception as e:
        logger.debug(f"Mois budgétaire indisponible, repli sur le mois civil : {e}")
    today = date.today()
    return today.year, today.month
