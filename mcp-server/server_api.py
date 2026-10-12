"""
Serveur MCP pour Suivi Budget — Mode Proxy API
================================================
Proxy MCP en lecture seule vers l'API FastAPI : les KPI sont calculés par le backend.
Aucun outil d'écriture ; l'API refuse d'ailleurs toute requête autre que GET avec un token MCP.

Architecture :
  [Claude Code] ←HTTPS (streamable-http)→ [Nginx /mcp] → [MCP Server] ←HTTP→ [API]
  [Client local] ←stdio→ [MCP Server] ←HTTP→ [API]

Sécurité :
  - Authentification par token MCP généré dans Numera (Paramètres → Compte), jamais par mot de passe
  - HTTP : le token du client (`Authorization: Bearer nmr_…`) est validé par le backend
    (`server_auth.py`) puis transmis tel quel à chaque appel API
  - stdio : token lu dans MCP_API_TOKEN
  - Le backend refuse les tokens révoqués, l'accès MCP désactivé et toute route /admin
  - Requêtes SQL brutes impossibles (pas d'accès direct à la DB)
"""

__version__ = "3.0.0"

import json
import os
import logging
from datetime import datetime
from urllib.parse import urlencode
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# ─── Configuration ───────────────────────────────────────────────────────────

# URL de base de l'API (dans Docker : http://backend:8001)
API_BASE_URL = os.environ.get("MCP_API_URL", "http://localhost:8001")

# Nom du serveur
SERVER_NAME = os.environ.get("MCP_SERVER_NAME", "Numera")

# Transport (stdio par défaut pour usage local)
TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")
HOST = os.environ.get("MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("MCP_PORT", "8100"))
HTTP_TRANSPORTS = ("sse", "streamable-http")

# stdio uniquement : token MCP généré dans l'interface (en HTTP, c'est celui du client)
API_TOKEN = os.environ.get("MCP_API_TOKEN")
if TRANSPORT not in HTTP_TRANSPORTS and not API_TOKEN:
    raise ValueError(
        "MCP_API_TOKEN doit être défini en transport stdio : générez un token dans Numera (Paramètres → Compte)"
    )

# Logging (sur stderr pour ne pas interférer avec stdio)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("mcp-suivi-budget")

# ─── Client HTTP ─────────────────────────────────────────────────────────────

class APIClient:
    """Client HTTP en lecture seule (GET) de l'API, authentifié par le token MCP (celui du client en HTTP, MCP_API_TOKEN en stdio)."""

    def __init__(self, base_url: str, static_token: str | None):
        self.base_url = base_url.rstrip("/")
        self._static_token = static_token
        self._client = httpx.Client(timeout=30.0)

    def _token(self) -> str:
        if self._static_token:
            return self._static_token
        # Transport HTTP : le middleware a déjà validé le token de la requête en cours
        request = mcp.get_context().request_context.request
        authorization = request.headers.get("authorization", "") if request is not None else ""
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise PermissionError("Aucun token MCP dans la requête")
        return token.strip()

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{path}"
        try:
            return self._client.request(method, url, headers={"Authorization": f"Bearer {self._token()}"}, **kwargs)
        except httpx.ConnectError as e:
            raise ConnectionError(
                f"❌ Impossible de joindre l'API ({self.base_url}). Vérifiez MCP_API_URL."
            ) from e

    def get(self, path: str, params: dict | None = None) -> httpx.Response:
        return self._request("GET", path, params=params)

    def close(self):
        self._client.close()


api = APIClient(API_BASE_URL, API_TOKEN if TRANSPORT not in HTTP_TRANSPORTS else None)

# ─── Initialisation du serveur MCP ───────────────────────────────────────────

mcp = FastMCP(
    SERVER_NAME,
    # Sans état : chaque requête HTTP est autonome (pas d'affinité de session derrière Nginx)
    stateless_http=True,
    # La protection DNS rebinding n'autorise que localhost ; derrière Nginx, l'hôte est le domaine public.
    # Inutile ici : l'accès repose sur un token bearer explicite, pas sur un accès réseau local.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

# ─── Helpers de formatage ────────────────────────────────────────────────────

def serialize(obj: Any) -> str:
    """Sérialise en JSON lisible."""
    return json.dumps(obj, indent=2, default=str, ensure_ascii=False)


def format_table(rows: list[dict], max_col_width: int = 40) -> str:
    """Formate des résultats en table lisible."""
    if not rows:
        return "Aucun résultat."

    columns = list(rows[0].keys())
    widths = {}
    for col in columns:
        values = [str(row.get(col, "")) for row in rows]
        widths[col] = min(max(len(col), max(len(v) for v in values)), max_col_width)

    header = " | ".join(col.ljust(widths[col])[:widths[col]] for col in columns)
    separator = "-+-".join("-" * widths[col] for col in columns)
    lines = [header, separator]
    for row in rows:
        line = " | ".join(
            str(row.get(col, "")).ljust(widths[col])[:widths[col]]
            for col in columns
        )
        lines.append(line)
    return "\n".join(lines)


def handle_response(resp: httpx.Response, label: str = "") -> str:
    """Gère la réponse API et retourne un message formaté."""
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return f"❌ Erreur API ({resp.status_code}) : {detail}"
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCES — Données accessibles par le LLM
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.resource("data://accounts")
def resource_accounts() -> str:
    """Liste tous les comptes bancaires."""
    resp = api.get("/accounts")
    error = handle_response(resp, "comptes")
    if error:
        return error
    return serialize(resp.json())


@mcp.resource("data://categories")
def resource_categories() -> str:
    """Liste toutes les catégories."""
    resp = api.get("/categories")
    error = handle_response(resp)
    if error:
        return error
    return serialize(resp.json())


@mcp.resource("data://tags")
def resource_tags() -> str:
    """Liste tous les tags."""
    resp = api.get("/tags")
    error = handle_response(resp)
    if error:
        return error
    return serialize(resp.json())


@mcp.resource("data://recurring-transactions")
def resource_recurring() -> str:
    """Liste toutes les transactions récurrentes (abonnements)."""
    resp = api.get("/recurring-transactions/")
    error = handle_response(resp)
    if error:
        return error
    return serialize(resp.json())


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS — Lecture / Consultation
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
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


@mcp.tool()
def list_categories() -> str:
    """Liste toutes les catégories de dépenses et revenus avec leurs limites budgétaires."""
    try:
        resp = api.get("/categories")
        error = handle_response(resp)
        if error:
            return error
        categories = resp.json()
        return f"🏷️ {len(categories)} catégorie(s) :\n\n" + format_table(categories)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def list_transactions(
    account_id: int | None = None,
    category_id: int | None = None,
    type: str | None = None,
    merchant: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    is_transfer: bool | None = None,
    limit: int = 50,
) -> str:
    """Liste les transactions avec filtres.

    Args:
        account_id: Filtrer par compte (ID)
        category_id: Filtrer par catégorie (ID)
        type: Filtrer par type (Entree, Sortie, Interets, Solde Initial)
        merchant: Recherche partielle dans le nom du marchand
        start_date: Date de début (YYYY-MM-DDTHH:MM:SS)
        end_date: Date de fin (YYYY-MM-DDTHH:MM:SS)
        search: Recherche texte dans marchand et note
        min_amount: Montant minimum
        max_amount: Montant maximum
        is_transfer: Filtrer les virements internes (true/false)
        limit: Nombre max de résultats (défaut 50, max 200)
    """
    try:
        params: dict[str, Any] = {"limit": min(limit, 200)}
        if account_id is not None:
            params["account_id"] = account_id
        if category_id is not None:
            params["category_id"] = category_id
        if type:
            params["type"] = type
        if merchant:
            params["merchant"] = merchant
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if search:
            params["search"] = search
        if min_amount is not None:
            params["min_amount"] = min_amount
        if max_amount is not None:
            params["max_amount"] = max_amount
        if is_transfer is not None:
            params["is_transfer"] = is_transfer

        resp = api.get("/transactions", params=params)
        error = handle_response(resp)
        if error:
            return error
        transactions = resp.json()

        # Simplifier pour la lisibilité
        simplified = []
        for tx in transactions:
            simplified.append({
                "id": tx["id"],
                "date": tx["date"][:10] if tx.get("date") else "",
                "type": tx.get("type", ""),
                "merchant": tx.get("merchant", ""),
                "amount": tx.get("amount", 0),
                "currency": tx.get("currency", "EUR"),
                "categorie": tx.get("category", {}).get("name", "—") if tx.get("category") else "—",
                "note": tx.get("note", "") or "",
                "solde": tx.get("running_balance", 0),
            })

        return f"📊 {len(simplified)} transaction(s) :\n\n" + format_table(simplified)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_transaction(transaction_id: int) -> str:
    """Récupère le détail complet d'une transaction par son ID.

    Args:
        transaction_id: L'ID de la transaction
    """
    try:
        # L'API n'a pas de GET /{id}, on filtre via la liste
        resp = api.get("/transactions", params={"limit": 1000})
        error = handle_response(resp)
        if error:
            return error

        transactions = resp.json()
        tx = next((t for t in transactions if t["id"] == transaction_id), None)
        if not tx:
            return f"❌ Transaction #{transaction_id} introuvable."
        return serialize(tx)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def search_transactions(query: str, limit: int = 20) -> str:
    """Recherche textuelle dans les transactions (marchand et note).

    Args:
        query: Texte à rechercher
        limit: Nombre max de résultats (défaut 20)
    """
    try:
        resp = api.get("/transactions", params={
            "search": query,
            "limit": min(limit, 100)
        })
        error = handle_response(resp)
        if error:
            return error
        transactions = resp.json()

        simplified = []
        for tx in transactions:
            simplified.append({
                "id": tx["id"],
                "date": tx["date"][:10] if tx.get("date") else "",
                "type": tx.get("type", ""),
                "merchant": tx.get("merchant", ""),
                "amount": tx.get("amount", 0),
                "categorie": tx.get("category", {}).get("name", "—") if tx.get("category") else "—",
                "note": tx.get("note", "") or "",
            })

        return f"🔍 {len(simplified)} résultat(s) pour '{query}' :\n\n" + format_table(simplified)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def list_merchants() -> str:
    """Liste tous les marchands distincts présents dans les transactions."""
    try:
        resp = api.get("/transactions/merchants")
        error = handle_response(resp)
        if error:
            return error
        merchants = resp.json()
        return f"🏪 {len(merchants)} marchand(s) :\n" + "\n".join(f"  • {m}" for m in merchants)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def list_recurring_transactions() -> str:
    """Liste les transactions récurrentes (abonnements, salaires, etc.)."""
    try:
        resp = api.get("/recurring-transactions/")
        error = handle_response(resp)
        if error:
            return error
        items = resp.json()

        simplified = []
        for rt in items:
            simplified.append({
                "id": rt["id"],
                "name": rt.get("name", ""),
                "type": rt.get("type", ""),
                "amount": rt.get("amount", 0),
                "frequency": rt.get("frequency", ""),
                "is_active": rt.get("is_active", False),
                "categorie": rt.get("category", {}).get("name", "—") if rt.get("category") else "—",
                "day": rt.get("day_of_month", "—"),
            })

        return f"🔄 {len(simplified)} récurrence(s) :\n\n" + format_table(simplified)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def list_savings_goals() -> str:
    """Liste tous les objectifs d'épargne avec leur progression."""
    try:
        resp = api.get("/goals")
        error = handle_response(resp)
        if error:
            return error
        goals = resp.json()

        simplified = []
        for g in goals:
            simplified.append({
                "id": g["id"],
                "name": g.get("name", ""),
                "cible": g.get("target_amount", 0),
                "actuel": g.get("current_amount", 0),
                "progression_%": g.get("percentage", 0),
                "statut": g.get("status", "—"),
                "deadline": g.get("deadline", "—") or "—",
                "mensuel_requis": g.get("monthly_required", "—") or "—",
            })

        return f"🎯 {len(simplified)} objectif(s) :\n\n" + format_table(simplified)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def list_tags() -> str:
    """Liste tous les tags disponibles."""
    try:
        resp = api.get("/tags")
        error = handle_response(resp)
        if error:
            return error
        tags = resp.json()
        return f"🏷️ {len(tags)} tag(s) :\n\n" + format_table(tags)
    except Exception as e:
        return f"❌ Erreur : {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS — Analytics
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_budget_summary(month: int | None = None, year: int | None = None, account_id: int | None = None) -> str:
    """Résumé budget complet : revenus, dépenses par catégorie, soldes des comptes.

    Args:
        month: Mois (1-12, optionnel, défaut: mois en cours)
        year: Année (optionnel, défaut: année en cours)
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

        resp = api.get("/analytics/budget", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"📊 Résumé budget :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
def get_budget_alerts() -> str:
    """Alertes budgétaires : catégories proches ou dépassant les limites."""
    try:
        resp = api.get("/analytics/budget-alerts")
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
            annual_ratio = alert.get("annual_ratio")
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


@mcp.tool()
def get_insights() -> str:
    """Insights intelligents : score de santé financière, tendances, recommandations."""
    try:
        resp = api.get("/analytics/insights")
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"🧠 Insights financiers :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_monthly_report(month: int | None = None, year: int | None = None) -> str:
    """Rapport mensuel complet avec comparaison au mois précédent.

    Args:
        month: Mois (1-12, optionnel, défaut: mois en cours)
        year: Année (optionnel, défaut: année en cours)
    """
    try:
        params: dict[str, Any] = {}
        if month is not None:
            params["month"] = month
        if year is not None:
            params["year"] = year

        resp = api.get("/analytics/monthly-report", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"📊 Rapport mensuel :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_kpi_history(months: int = 6) -> str:
    """Historique des KPIs financiers sur N mois (revenus, dépenses, épargne, etc.).

    Args:
        months: Nombre de mois d'historique (défaut 6)
    """
    try:
        resp = api.get("/analytics/kpi-history", params={"months": min(months, 24)})
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"📈 Historique KPI ({months} mois) :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


@mcp.tool()
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


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS — Portfolio & ETF
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
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


@mcp.tool()
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
        return f"🏛️ Fiscalité {data['year']} — {len(rows)} enveloppe(s) :\n\n" + format_table(rows)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def list_transfer_rules() -> str:
    """Règles de virement interne (compte source → compte destination) qui relient automatiquement
    les sorties aux entrées pour ne pas compter deux fois un revenu réparti entre comptes."""
    try:
        resp = api.get("/transfer-rules")
        error = handle_response(resp)
        if error:
            return error
        accounts = {a["id"]: a["name"] for a in api.get("/accounts").json()}
        rows = [
            {
                "id": r["id"],
                "source": accounts.get(r["source_account_id"], r["source_account_id"]),
                "destination": accounts.get(r["dest_account_id"], r["dest_account_id"]),
                "libelle_contient": r["pattern"] or "—",
                "montant": r["amount"] if r["amount"] is not None else "—",
                "tolerance_%": r["amount_tolerance_pct"],
                "tolerance_jours": r["day_tolerance"],
                "active": "oui" if r["is_active"] else "non",
            }
            for r in resp.json()
        ]
        return f"🔁 {len(rows)} règle(s) de virement :\n\n" + (format_table(rows) if rows else "Aucune règle.")
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def list_reimbursement_claims(status: str = "open", debtor: str | None = None) -> str:
    """Créances de remboursement (« ce qu'on me doit ») : dépense, débiteur, attendu, reçu, reste dû.
    `status` : open (reste dû > 0, défaut), settled ou all."""
    try:
        params = {"status": status}
        if debtor:
            params["debtor"] = debtor
        resp = api.get("/reimbursements/claims", params=params)
        error = handle_response(resp)
        if error:
            return error
        rows = [
            {
                "id": c["id"],
                "date": c["expense"]["date"][:10],
                "depense": c["expense"]["label"],
                "debiteur": c["debtor"],
                "attendu": c["expected_amount"],
                "recu": c["received"],
                "reste_du": c["remaining"],
            }
            for c in resp.json()
        ]
        total = round(sum(r["reste_du"] for r in rows), 2)
        return f"💸 {len(rows)} créance(s), {total} restant dû :\n\n" + (format_table(rows) if rows else "Aucune créance.")
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
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


@mcp.tool()
def list_etf_profiles() -> str:
    """Liste tous les profils ETF connus avec leur composition par pays, secteurs et top holdings.

    Utile pour comprendre ce que contient réellement un ETF.
    Les profils système (is_system ✅) sont intégrés à Numera, les autres (📝) créés à l'usage.
    Secteurs et top 10 viennent de Yahoo Finance (actualisés chaque semaine) ; la répartition
    par pays n'est jamais fournie par Yahoo : préréglage intégré ou saisie, sinon vide.
    """
    try:
        resp = api.get("/etf-profiles")
        error = handle_response(resp)
        if error:
            return error
        profiles = resp.json()
        simplified = []
        for p in profiles:
            top = p.get("top_holdings", [])
            top_names = ", ".join(h.get("name", "") for h in top[:3]) if top else "—"
            countries = p.get("countries", {})
            top_countries = ", ".join(list(countries.keys())[:3]) if countries else "—"
            simplified.append({
                "id": p["id"],
                "nom": p.get("name", ""),
                "ticker": p.get("ticker", ""),
                "isin": p.get("isin") or "—",
                "top_pays": top_countries,
                "top_holdings": top_names,
                "systeme": "✅" if p.get("is_system") else "📝",
            })
        return f"🗂️ {len(simplified)} profil(s) ETF :\n\n" + format_table(simplified)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_etf_profile(profile_id: int) -> str:
    """Récupère le détail complet d'un profil ETF : pays (%), secteurs (%) et top 10 positions.

    Args:
        profile_id: ID du profil ETF (obtenir via list_etf_profiles)
    """
    try:
        resp = api.get(f"/etf-profiles/{profile_id}")
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        source_labels = {"yahoo": "Yahoo Finance", "preset": "préréglage", "manual": "saisie manuelle"}
        sources = data.get("composition_sources") or {}
        lines = [
            f"🗂️ ETF : {data.get('name', '')} ({data.get('ticker', '')})",
            f"   ISIN : {data.get('isin') or '—'}",
            "   Sources : " + ", ".join(
                f"{label} = {source_labels.get(sources.get(field), 'non renseigné')}"
                for field, label in (("countries", "pays"), ("sectors", "secteurs"), ("top_holdings", "top 10"))
            ),
            f"   Actualisé le : {data.get('composition_refreshed_at') or 'jamais'}",
            "",
        ]
        countries = data.get("countries", {})
        if countries:
            lines.append("🌍 Pays :")
            for country, pct in sorted(countries.items(), key=lambda x: -float(x[1]))[:10]:
                lines.append(f"  • {country} : {pct}%")
            lines.append("")
        sectors = data.get("sectors", {})
        if sectors:
            lines.append("🏭 Secteurs :")
            for sector, pct in sorted(sectors.items(), key=lambda x: -float(x[1]))[:10]:
                lines.append(f"  • {sector} : {pct}%")
            lines.append("")
        top_holdings = data.get("top_holdings", [])
        if top_holdings:
            lines.append("🏢 Top Holdings :")
            for h in top_holdings[:10]:
                ticker_str = f" ({h.get('ticker')})" if h.get("ticker") else ""
                lines.append(f"  • {h.get('name', '')}{ticker_str} : {h.get('weight', 0)}%")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_diversity_scanner(account_id: int | None = None) -> str:
    """Analyse complète de diversification du portefeuille avec décomposition ETF (look-through).

    ⏱️ Cet outil peut prendre quelques secondes : il récupère les cours live
    et peut créer depuis Yahoo le profil des ETF non encore profilés. La part d'un ETF
    dont la composition n'est pas connue est comptée en « Non renseigné ».

    Retourne :
    - Score de diversité HHI (0-100) : 90+ = excellent, 60-90 = bon, <60 = à améliorer
    - Exposition réelle par entreprise sous-jacente (directe + via ETF look-through)
    - Répartition par pays et secteur (à travers tous les ETF)
    - Alertes : surconcentration, chevauchements (doublons ETF), biais géographique
    - Totaux : valeur actions/ETF, épargne, liquidités, fonds euros (contexte patrimoine complet)

    Args:
        account_id: Filtrer par compte d'investissement (optionnel, défaut = tous)
    """
    try:
        params: dict[str, Any] = {}
        if account_id is not None:
            params["account_id"] = account_id
        resp = api.get("/analytics/diversity-scanner", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()

        lines = [
            f"🎯 Score de diversité : {data.get('score', '—')}/100 — {data.get('score_label', '')}",
            "",
        ]

        totals = data.get("totals", {})
        lines.append(f"💼 Valeur totale actions/ETF : {totals.get('stocks_eur', 0):,.2f} €")
        lines.append(f"🏦 Épargne : {totals.get('epargne_eur', 0):,.2f} €")
        lines.append(f"💳 Liquidités (courant) : {totals.get('courant_eur', 0):,.2f} €")
        lines.append(f"🔐 Fonds euros : {totals.get('fonds_euros_eur', 0):,.2f} €")
        lines.append(f"🌍 Patrimoine total : {totals.get('wealth_eur', 0):,.2f} €")
        lines.append(f"   ({totals.get('holdings_count', 0)} positions dont {totals.get('etfs_count', 0)} ETF)")
        lines.append("")

        companies = data.get("top_underlying_companies", [])
        if companies:
            lines.append(f"🏢 Top entreprises sous-jacentes ({len(companies)}) :")
            for c in companies[:10]:
                overlap = " 🔁 doublon" if c.get("has_overlap") else ""
                lines.append(
                    f"  • {c['name']} ({c.get('ticker') or '?'}) : "
                    f"{c['pct_stocks']}% actions / {c['pct_total_wealth']}% patrimoine{overlap}"
                )
            lines.append("")

        countries = data.get("countries", [])
        if countries:
            lines.append("🌍 Répartition géographique (look-through ETF) :")
            for c in countries[:8]:
                lines.append(
                    f"  • {c['name']} : {c['percentage_stocks']}% des actions "
                    f"({c['percentage_total_wealth']}% du patrimoine)"
                )
            lines.append("")

        sectors = data.get("sectors", [])
        if sectors:
            lines.append("🏭 Répartition sectorielle (look-through ETF) :")
            for s in sectors[:8]:
                lines.append(
                    f"  • {s['name']} : {s['percentage_stocks']}% des actions "
                    f"({s['percentage_total_wealth']}% du patrimoine)"
                )
            lines.append("")

        alerts = data.get("alerts", [])
        if alerts:
            lines.append(f"⚠️ {len(alerts)} alerte(s) de diversification :")
            for a in alerts:
                icon = "🔴" if a.get("type") == "danger" else ("🟠" if a.get("type") == "warning" else "🔵")
                lines.append(f"  {icon} {a.get('title', '')}")
                lines.append(f"     {a.get('message', '')}")
        else:
            lines.append("✅ Aucune alerte de diversification.")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
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


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS — Templates pour l'agent IA
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.prompt()
def analyze_month(month: int, year: int) -> str:
    """Analyse complète d'un mois de budget.

    Args:
        month: Mois (1-12)
        year: Année
    """
    return f"""Analyse complète du budget pour {month:02d}/{year}.

Étapes :
1. `get_budget_summary(month={month}, year={year})` — vue d'ensemble
2. `get_expenses_by_category(month={month}, year={year})` — répartition
3. `get_top_merchants(month={month}, year={year})` — marchands principaux
4. `get_budget_alerts()` — alertes budget
5. `get_monthly_report(month={month}, year={year})` — rapport complet avec comparaison

Fournis :
- Résumé revenus / dépenses / solde
- Top 5 catégories et marchands
- Alertes budget
- Comparaison avec le mois précédent
- Recommandations d'optimisation
"""


@mcp.prompt()
def audit_subscriptions() -> str:
    """Audit complet des abonnements et charges récurrentes."""
    return """Audit des abonnements et charges récurrentes.

Étapes :
1. `list_recurring_transactions()` — abonnements déclarés
2. `get_subscriptions()` — analyse détectée automatiquement
3. `search_transactions("abonnement")` — rechercher dans les transactions

Pour chaque abonnement :
- Nom, montant, fréquence
- Catégorie
- Toujours pertinent ?

Synthèse :
- Coût total mensuel et annuel
- Recommandations d'optimisation
- Abonnements potentiellement oubliés
"""


@mcp.prompt()
def budget_review() -> str:
    """Review complète et approfondie du budget."""
    return """Review complète des finances.

Étapes :
1. `list_accounts()` — comptes et soldes
2. `get_kpi_history(months=12)` — tendances annuelles
3. `get_budget_summary()` — mois en cours
4. `get_insights()` — score de santé financière
5. `list_recurring_transactions()` — charges fixes
6. `list_savings_goals()` — objectifs d'épargne
7. `get_cashflow_projection()` — projection trésorerie

Rapport structuré :
## 1. Situation globale (soldes, évolution)
## 2. Revenus vs Dépenses (moyennes, taux d'épargne)
## 3. Top catégories (postes principaux, économies possibles)
## 4. Abonnements (total, recommandations)
## 5. Objectifs d'épargne (progression)
## 6. Projection et recommandations
"""


@mcp.prompt()
def categorize_uncategorized() -> str:
    """Propose des catégories pour les transactions qui n'en ont pas (sans rien modifier)."""
    return """Trouve les transactions sans catégorie et propose une catégorie pour chacune.

Étapes :
1. `list_categories()` — voir les catégories existantes
2. `list_transactions(limit=200)` — chercher les transactions sans catégorie
3. Groupe-les par marchand et propose une catégorie existante pour chaque marchand
4. Présente le résultat en tableau (marchand, nb de transactions, catégorie proposée)

Le serveur MCP est en lecture seule : l'utilisateur applique les catégories dans Numera
(Paramètres → Règles, pour une règle d'auto-catégorisation par marchand).
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS — Portfolio & ETF
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.prompt()
def analyze_portfolio() -> str:
    """Analyse complète du portefeuille d'investissement : positions, performance, diversification."""
    return """Analyse complète du portefeuille d'investissement.

Étapes :
1. `list_accounts(type="investissement")` — identifier les comptes d'investissement
2. `list_holdings()` — positions actuelles avec prix live et performance
3. `get_investments_summary()` — résumé global (net investi, valeur totale, gain)
4. `get_diversity_scanner()` — décomposition ETF look-through + score de diversité + alertes
5. `list_etf_profiles()` — profils ETF connus pour contexte
6. `get_investments_allocation_advanced()` — répartition par classe d'actif, secteur, zone géo

Rapport structuré attendu :
## 1. Vue d'ensemble
- Valeur totale du portefeuille, net investi, gain total, performance %
- Nombre de positions (dont ETF vs actions directes)

## 2. Positions actuelles
- Top positions par valeur (ticker, nom, valeur, gain %)
- ETF détenus et leur poids dans le portefeuille

## 3. Analyse de diversification (look-through ETF)
- Score de diversité (X/100) avec interprétation
- Top 10 entreprises sous-jacentes réelles (directes + via ETF)
- Répartition géographique et sectorielle

## 4. Alertes & Risques
- Surconcentrations détectées
- Chevauchements / doublons d'exposition
- Biais géographiques

## 5. Recommandations de rééquilibrage
"""


@mcp.prompt()
def analyze_etf_lookthrough() -> str:
    """Décompose les ETF détenus pour révéler les entreprises réelles sous-jacentes et les doublons."""
    return """Décomposition ETF et analyse look-through.

Étapes :
1. `list_holdings()` — identifier les ETF dans le portefeuille (colonne etf = ✅)
2. `list_etf_profiles()` — voir les profils disponibles
3. `get_etf_profile(profile_id)` — détail de chaque profil ETF détenu (pays, secteurs, top 10)
4. `get_diversity_scanner()` — exposition réelle complète (look-through tous les ETF)

Pour chaque ETF détenu :
- Quel est son profil géographique (USA, Europe, Monde ?) ?
- Quels sont ses top holdings (Apple, Microsoft, Amazon, LVMH ?) ?
- Y a-t-il des chevauchements avec d'autres ETF ou actions directes ?

Rapport :
## 1. ETF détenus et leur poids dans le portefeuille
## 2. Décomposition de chaque ETF (top pays, secteurs, holdings)
## 3. Top 10 entreprises sous-jacentes agrégées (doublons additionnnés)
## 4. Chevauchements identifiés (titres présents dans plusieurs ETF ou en direct ET en ETF)
## 5. Recommandations (consolider, diversifier, remplacer un ETF redondant ?)
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Point d'entrée
# ═══════════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    logger.info(f"Démarrage du serveur MCP '{SERVER_NAME}' v{__version__}")
    logger.info(f"API cible : {API_BASE_URL}")
    logger.info(f"Transport : {TRANSPORT}")

    if TRANSPORT in HTTP_TRANSPORTS:
        import uvicorn
        from server_auth import protect

        app = mcp.streamable_http_app() if TRANSPORT == "streamable-http" else mcp.sse_app()
        logger.info(f"Écoute sur {HOST}:{PORT} (tokens MCP validés par l'API)")
        uvicorn.run(protect(app, API_BASE_URL), host=HOST, port=PORT, proxy_headers=True, forwarded_allow_ips="*")
    else:
        mcp.run(transport="stdio")
