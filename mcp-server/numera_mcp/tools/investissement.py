"""Outils MCP du domaine investissement (portefeuille, positions, dividendes, ETF, fiscalité)."""

from typing import Any

from numera_mcp.api_client import api, handle_response
from numera_mcp.formatting import format_table, serialize


def get_portfolio(account_id: int | None = None) -> str:
    """Valeur calculée (positions × cours + espèces), plus-values, XIRR/TWR et rapprochement.

    Sans `account_id` : vue globale (somme EUR des comptes titres valorisés par positions, plus-values
    réalisées par année pour la déclaration, dividendes, frais, XIRR global). Avec `account_id` : valeur,
    espèces, montant investi, plus-value latente (dont effet de change par ligne), plus-value réalisée,
    dividendes, frais, XIRR, TWR, courbe reconstituée et écart avec les relevés du courtier.
    `value_source` vaut "positions" (PEA/CTO/crypto) ou "snapshot" (assurance-vie, compte sans positions).

    Args:
        account_id: ID du compte d'investissement (optionnel)
    """
    try:
        resp = api.get(f"/analytics/portfolio/{account_id}" if account_id is not None else "/analytics/portfolio")
        error = handle_response(resp)
        if error:
            return error
        return f"📈 Portefeuille :\n\n{serialize(resp.json())}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_dividends(account_id: int | None = None, months: int = 24) -> str:
    """Dividendes reçus (EUR) : totaux net/brut/retenues, 12 derniers mois, par mois, par année et par titre.

    Chaque titre porte son rendement sur PRU (12 derniers mois ÷ coût de revient) et son rendement
    actuel (÷ valeur de la position). `unlinked` compte les dividendes encore sans titre.

    Args:
        account_id: Filtrer par compte d'investissement (optionnel)
        months: Nombre de mois de la série mensuelle (défaut 24, max 120)
    """
    try:
        params: dict[str, Any] = {"months": months}
        if account_id is not None:
            params["account_id"] = account_id
        resp = api.get("/analytics/dividends", params=params)
        error = handle_response(resp)
        if error:
            return error
        return f"💶 Dividendes :\n\n{serialize(resp.json())}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_investments_summary(
    account_id: int | None = None,
    month: int | None = None,
    year: int | None = None,
) -> str:
    """Résumé des investissements (comptes d'investissement actifs).

    Args:
        account_id: Filtrer par compte spécifique (optionnel)
        month: Mois (1-12, optionnel)
        year: Année (optionnel)
    """
    try:
        params: dict[str, Any] = {}
        if account_id is not None:
            params["account_id"] = account_id
        if month is not None:
            params["month"] = month
        if year is not None:
            params["year"] = year

        resp = api.get("/analytics/investments", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"📈 Investissements :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_investment_performance(account_id: int) -> str:
    """Analyse de performance détaillée d'un compte d'investissement spécifique.

    Args:
        account_id: ID du compte d'investissement
    """
    try:
        resp = api.get(f"/analytics/investments/{account_id}")
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"📊 Performance de l'investissement #{account_id} :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_investment_performance_history(account_id: int, months: int = 12) -> str:
    """Historique des performances mensuelles d'un compte d'investissement spécifique.

    Args:
        account_id: ID du compte d'investissement
        months: Nombre de mois (défaut 12)
    """
    try:
        resp = api.get(f"/analytics/investments/{account_id}/performance-history", params={"months": months})
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"📈 Historique des performances de l'investissement #{account_id} :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_investments_allocation(account_id: int | None = None) -> str:
    """Répartition de l'allocation d'actifs globale ou pour un compte spécifique.

    Args:
        account_id: Filtrer par compte spécifique (optionnel)
    """
    try:
        params: dict[str, Any] = {}
        if account_id is not None:
            params["account_id"] = account_id
        resp = api.get("/analytics/investments-allocation", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"🧩 Allocation des investissements :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_investments_allocation_advanced() -> str:
    """Allocation d'actifs détaillée avancée par classe, secteur et zone géographique."""
    try:
        resp = api.get("/analytics/investments-allocation-advanced")
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"🔬 Allocation avancée et suggestions de rééquilibrage :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def list_holdings(account_id: int | None = None) -> str:
    """Liste toutes les positions du portefeuille (actions et ETF) avec prix live, performance et gain.

    Chaque position inclut :
    - ticker, ISIN, nom de l'actif
    - quantité et prix moyen d'achat (buy_price_avg)
    - prix actuel et valeur actuelle en EUR
    - gain en EUR et pourcentage de performance
    - si c'est un ETF (is_etf)

    Args:
        account_id: Filtrer par compte d'investissement (optionnel)
    """
    try:
        params: dict[str, Any] = {}
        if account_id is not None:
            params["account_id"] = account_id
        resp = api.get("/holdings", params=params)
        error = handle_response(resp)
        if error:
            return error
        holdings = resp.json()
        simplified = []
        for h in holdings:
            simplified.append({
                "id": h["id"],
                "compte": h.get("account_id"),
                "ticker": h.get("ticker", ""),
                "nom": h.get("asset_name", ""),
                "isin": h.get("isin") or "—",
                "quantite": h.get("quantity", 0),
                "px_achat_moy": h.get("buy_price_avg") or "—",
                "px_actuel_EUR": h.get("current_price_eur") or "—",
                "valeur_EUR": h.get("current_value_eur") or "—",
                "investi_EUR": h.get("total_invested_eur") or "—",
                "gain_EUR": h.get("gain_eur") or "—",
                "gain_%": h.get("gain_pct") or "—",
                "etf": "✅" if h.get("is_etf") else "📈",
            })
        return f"📊 {len(simplified)} position(s) :\n\n" + format_table(simplified)
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_tax_overview() -> str:
    """Plafonds, place restante et dates clés des enveloppes fiscales (PEA, PER, Livret A, assurance-vie).

    Chaque enveloppe indique le montant courant, le plafond, la place restante, l'ancienneté
    face aux 5 ans (PEA) ou 8 ans (assurance-vie) et les alertes éventuelles.
    """
    try:
        resp = api.get("/tax/overview")
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        rows = [
            {
                "compte": w["account_name"],
                "enveloppe": w["kind"],
                "courant_EUR": w["current"] if w["current"] is not None else "—",
                "plafond_EUR": w["ceiling"] if w["ceiling"] is not None else "—",
                "restant_EUR": w["remaining"] if w["remaining"] is not None else "—",
                "anciennete_ans": round(w["age_years"], 1) if w["age_years"] is not None else "—",
                "alertes": "; ".join(w["alerts"]) or "—",
            }
            for w in data["wrappers"]
        ]
        text = f"🏛️ Fiscalité {data['year']} — {len(rows)} enveloppe(s) :\n\n" + format_table(rows)
        advice = data.get("allocation_advice") or []
        if advice:
            text += "\n\n🧭 Où placer le prochain euro (ordre conseillé) :\n" + "\n".join(
                f"{a['rank']}. {a['account_name'] or a['kind']} — {a['reason']}" for a in advice
            )
        return text
    except Exception as e:
        return f"❌ Erreur : {e}"


def list_investment_transactions(account_id: int | None = None, limit: int = 50) -> str:
    """Liste les transactions d'investissement : achats, ventes et dividendes avec ticker, ISIN, quantité et prix unitaire.

    Ces transactions sont distinctes des transactions bancaires classiques.
    Elles tracent les opérations sur titres (actions / ETF).

    Types : versement / retrait (flux d'espèces, avec titre = dépôt + achat / vente + retrait),
    achat / vente (opération sur titres, sans effet sur le montant investi), dividende (ticker obligatoire), frais

    Args:
        account_id: Filtrer par compte d'investissement (optionnel)
        limit: Nombre max de résultats (défaut 50, max 500)
    """
    try:
        params: dict[str, Any] = {"limit": min(limit, 500)}
        if account_id is not None:
            params["account_id"] = account_id
        resp = api.get("/investment-transactions", params=params)
        error = handle_response(resp)
        if error:
            return error
        txs = resp.json()
        simplified = []
        for tx in txs:
            simplified.append({
                "id": tx["id"],
                "date": tx["date"][:10] if tx.get("date") else "",
                "type": tx.get("type", ""),
                "ticker": tx.get("ticker") or "—",
                "isin": tx.get("isin") or "—",
                "quantite": tx.get("quantity") or "—",
                "px_unit": tx.get("unit_price") or "—",
                "montant": tx.get("amount", 0),
                "devise": tx.get("currency", "EUR"),
                "note": (tx.get("note") or "")[:40],
            })
        return f"📈 {len(simplified)} transaction(s) d'investissement :\n\n" + format_table(simplified)
    except Exception as e:
        return f"❌ Erreur : {e}"


TOOLS = [
    get_portfolio,
    get_dividends,
    get_investments_summary,
    get_investment_performance,
    get_investment_performance_history,
    get_investments_allocation,
    get_investments_allocation_advanced,
    list_holdings,
    get_tax_overview,
    list_investment_transactions,
]


def register(mcp) -> None:
    for tool in TOOLS:
        mcp.tool()(tool)
