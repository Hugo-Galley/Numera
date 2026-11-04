"""Outils MCP du domaine comptes (comptes, prêts, événements financiers)."""


from numera_mcp.api_client import api, handle_response
from numera_mcp.formatting import format_table


def list_accounts(type: str | None = None) -> str:
    """Liste tous les comptes bancaires avec leur type, devise et statut.
    Pour connaître les soldes, utilise get_budget_summary ou get_analytics_budget.
    
    Args:
        type: Filtrer par type (ex: courant, epargne, investissement) (optionnel)
    """
    try:
        resp = api.get("/accounts")
        error = handle_response(resp)
        if error:
            return error
        accounts = resp.json()
        if type:
            accounts = [a for a in accounts if a.get("type") == type]
        return f"🏦 {len(accounts)} compte(s) :\n\n" + format_table(accounts)
    except ConnectionError as e:
        return str(e)
    except Exception as e:
        return f"❌ Erreur : {e}"


def list_financial_events(start: str | None = None, end: str | None = None) -> str:
    """Journal des décisions financières (résiliation, hausse d'épargne, changement d'allocation…),
    du plus récent au plus ancien. Sert à expliquer un changement visible sur les courbes.

    Args:
        start: Date de début incluse (AAAA-MM-JJ, optionnel)
        end: Date de fin incluse (AAAA-MM-JJ, optionnel)
    """
    try:
        params = {k: v for k, v in {"start": start, "end": end}.items() if v}
        resp = api.get("/financial-events", params=params)
        error = handle_response(resp)
        if error:
            return error
        events = resp.json()
        if not events:
            return "Aucune décision notée dans le journal."
        simplified = [
            {
                "date": e["date"],
                "decision": e["title"],
                "note": e["note"] or "—",
                "compte": e["account_name"] or "—",
            }
            for e in events
        ]
        return f"📓 {len(simplified)} décision(s) :\n\n" + format_table(simplified)
    except Exception as e:
        return f"❌ Erreur : {e}"


def list_loans() -> str:
    """Crédits en cours : mensualité (hors assurance), capital restant dû (déduit du patrimoine net),
    part remboursée, date de fin, coût total des intérêts et de l'assurance."""
    try:
        resp = api.get("/loans")
        error = handle_response(resp)
        if error:
            return error
        loans = resp.json()
        if not loans:
            return "Aucun crédit enregistré."
        simplified = [
            {
                "id": loan["id"],
                "crédit": loan["name"],
                "type": loan["kind"],
                "taux": f"{loan['annual_rate_pct']} %",
                "mensualité": loan["monthly_payment"],
                "restant_dû": loan["remaining_principal"],
                "remboursé": f"{loan['repaid_pct']} %",
                "fin": loan["end_date"],
                "coût_total": loan["total_cost"],
            }
            for loan in loans
        ]
        return f"🏦 {len(simplified)} crédit(s) :\n\n" + format_table(simplified)
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_loan_schedule(loan_id: int, year: int | None = None) -> str:
    """Tableau d'amortissement d'un crédit (échéance, intérêts, capital, assurance, capital restant dû).

    Args:
        loan_id: Identifiant du crédit (voir list_loans)
        year: Ne garder que les échéances de cette année (optionnel)
    """
    try:
        resp = api.get(f"/loans/{loan_id}/schedule")
        error = handle_response(resp)
        if error:
            return error
        rows = [r for r in resp.json() if year is None or r["date"].startswith(str(year))]
        if not rows:
            return "Aucune échéance pour cette période."
        return f"📅 {len(rows)} échéance(s) :\n\n" + format_table(rows)
    except Exception as e:
        return f"❌ Erreur : {e}"


TOOLS = [
    list_accounts,
    list_financial_events,
    list_loans,
    get_loan_schedule,
]


def register(mcp) -> None:
    for tool in TOOLS:
        mcp.tool()(tool)
