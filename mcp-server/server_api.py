"""
Serveur MCP pour Suivi Budget — Mode Proxy API
================================================
Se connecte à l'API FastAPI distante sur le VPS via HTTP.
Tourne en local (transport stdio) et proxifie les requêtes.

Architecture :
  [Claude Desktop / Cursor] ←stdio→ [MCP Server local] ←HTTP→ [API VPS]

Sécurité :
  - Authentification JWT vers l'API du VPS
  - Token rafraîchi automatiquement
  - Aucune donnée stockée localement
  - Requêtes SQL brutes impossibles (pas d'accès direct à la DB)
"""

__version__ = "2.0.0"

import json
import os
import logging
from datetime import datetime
from urllib.parse import urlencode
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# ─── Configuration ───────────────────────────────────────────────────────────

# URL de base de l'API sur le VPS (réseau local)
API_BASE_URL = os.environ.get("MCP_API_URL", "http://192.168.1.100:8001")

# Credentials pour l'auth JWT
API_USERNAME = os.environ.get("MCP_API_USERNAME", "admin")
API_PASSWORD = os.environ.get("MCP_API_PASSWORD")
if not API_PASSWORD:
    raise ValueError("MCP_API_PASSWORD environment variable must be set")

# Nom du serveur
SERVER_NAME = os.environ.get("MCP_SERVER_NAME", "Suivi Budget MCP")

# Transport (stdio par défaut pour usage local)
TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")
HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "8100"))

# Logging (sur stderr pour ne pas interférer avec stdio)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("mcp-suivi-budget")

# ─── Client HTTP avec auth JWT ──────────────────────────────────────────────

class APIClient:
    """Client HTTP pour l'API FastAPI du VPS avec gestion automatique du JWT."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._token: str | None = None
        self._client = httpx.Client(timeout=30.0)

    def _authenticate(self) -> None:
        """Obtient un token JWT via l'endpoint /auth/token."""
        try:
            resp = self._client.post(
                f"{self.base_url}/auth/token",
                data={"username": self.username, "password": self.password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]
            logger.info("✅ Authentification réussie auprès de l'API")
        except httpx.HTTPStatusError as e:
            raise ConnectionError(
                f"❌ Échec d'authentification ({e.response.status_code}). "
                f"Vérifiez MCP_API_USERNAME et MCP_API_PASSWORD."
            ) from e
        except httpx.ConnectError as e:
            raise ConnectionError(
                f"❌ Impossible de se connecter à {self.base_url}. "
                f"Vérifiez que le VPS est accessible et que MCP_API_URL est correct."
            ) from e

    @property
    def headers(self) -> dict[str, str]:
        if not self._token:
            self._authenticate()
        return {"Authorization": f"Bearer {self._token}"}

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Effectue une requête avec retry automatique si le token a expiré."""
        url = f"{self.base_url}{path}"

        # Premier essai
        resp = self._client.request(method, url, headers=self.headers, **kwargs)

        # Si 401/403, le token a peut-être expiré → re-auth et retry
        if resp.status_code in (401, 403):
            logger.info("🔄 Token expiré, re-authentification...")
            self._token = None
            resp = self._client.request(method, url, headers=self.headers, **kwargs)

        return resp

    def get(self, path: str, params: dict | None = None) -> httpx.Response:
        return self._request("GET", path, params=params)

    def post(self, path: str, json_data: dict | None = None) -> httpx.Response:
        return self._request("POST", path, json=json_data)

    def patch(self, path: str, json_data: dict | None = None) -> httpx.Response:
        return self._request("PATCH", path, json=json_data)

    def delete(self, path: str) -> httpx.Response:
        return self._request("DELETE", path)

    def close(self):
        self._client.close()


# Client global (initialisé au premier appel)
api = APIClient(API_BASE_URL, API_USERNAME, API_PASSWORD)

# ─── Initialisation du serveur MCP ───────────────────────────────────────────

mcp = FastMCP(SERVER_NAME)

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
def list_accounts() -> str:
    """Liste tous les comptes bancaires avec leur type, devise et statut.
    Pour connaître les soldes, utilise get_budget_summary ou get_analytics_budget."""
    try:
        resp = api.get("/accounts")
        error = handle_response(resp)
        if error:
            return error
        accounts = resp.json()
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
    limit: int = 10,
) -> str:
    """Top marchands par montant dépensé.

    Args:
        month: Mois (1-12, optionnel)
        year: Année (optionnel)
        limit: Nombre de marchands (défaut 10)
    """
    try:
        params: dict[str, Any] = {"limit": min(limit, 50)}
        if month is not None:
            params["month"] = month
        if year is not None:
            params["year"] = year

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
def get_investments_summary() -> str:
    """Résumé global des investissements (tous comptes d'investissement)."""
    try:
        resp = api.get("/analytics/investments")
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"📈 Investissements :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_money_flow(month: int | None = None, year: int | None = None) -> str:
    """Flux d'argent détaillé : d'où vient l'argent et où il va.

    Args:
        month: Mois (1-12, optionnel)
        year: Année (optionnel)
    """
    try:
        params: dict[str, Any] = {}
        if month is not None:
            params["month"] = month
        if year is not None:
            params["year"] = year

        resp = api.get("/analytics/money-flow", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"💸 Flux d'argent :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS — Écriture
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def add_transaction(
    account_id: int,
    date: str,
    type: str,
    merchant: str,
    amount: float,
    category_id: int | None = None,
    note: str | None = None,
    currency: str = "EUR",
    tag_ids: list[int] | None = None,
) -> str:
    """Ajoute une nouvelle transaction.

    Args:
        account_id: ID du compte bancaire
        date: Date (YYYY-MM-DDTHH:MM:SS)
        type: Type : Entree, Sortie, ou Interets
        merchant: Nom du marchand / description
        amount: Montant (toujours positif)
        category_id: ID de la catégorie (optionnel)
        note: Note additionnelle (optionnel)
        currency: Devise (défaut EUR)
        tag_ids: Liste d'IDs de tags (optionnel)
    """
    try:
        # Validation basique
        if type not in ("Entree", "Sortie", "Interets"):
            return "❌ Type invalide. Valeurs : Entree, Sortie, Interets"
        if amount <= 0:
            return "❌ Le montant doit être positif."

        # Normaliser la date
        if "T" not in date:
            date = date + "T00:00:00"

        payload: dict[str, Any] = {
            "account_id": account_id,
            "date": date,
            "type": type,
            "merchant": merchant,
            "amount": amount,
            "currency": currency,
        }
        if category_id is not None:
            payload["category_id"] = category_id
        if note:
            payload["note"] = note
        if tag_ids:
            payload["tag_ids"] = tag_ids

        resp = api.post("/transactions", json_data=payload)
        error = handle_response(resp)
        if error:
            return error

        tx = resp.json()
        return (
            f"✅ Transaction #{tx['id']} créée !\n"
            f"  📅 Date : {tx['date'][:10]}\n"
            f"  🏷️ Type : {tx['type']}\n"
            f"  🏪 Marchand : {tx['merchant']}\n"
            f"  💰 Montant : {tx['amount']:,.2f} {tx.get('currency', 'EUR')}\n"
            f"  📊 Solde après : {tx.get('running_balance', 0):,.2f} €\n"
        )
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def update_transaction(
    transaction_id: int,
    date: str | None = None,
    type: str | None = None,
    merchant: str | None = None,
    category_id: int | None = None,
    amount: float | None = None,
    note: str | None = None,
    tag_ids: list[int] | None = None,
) -> str:
    """Met à jour une transaction existante (mise à jour partielle).

    Args:
        transaction_id: ID de la transaction
        date: Nouvelle date (YYYY-MM-DDTHH:MM:SS, optionnel)
        type: Nouveau type (optionnel)
        merchant: Nouveau marchand (optionnel)
        category_id: Nouvelle catégorie ID (optionnel)
        amount: Nouveau montant (optionnel)
        note: Nouvelle note (optionnel)
        tag_ids: Nouveaux tag IDs (optionnel)
    """
    try:
        payload: dict[str, Any] = {}
        if date is not None:
            payload["date"] = date if "T" in date else date + "T00:00:00"
        if type is not None:
            payload["type"] = type
        if merchant is not None:
            payload["merchant"] = merchant
        if category_id is not None:
            payload["category_id"] = category_id
        if amount is not None:
            payload["amount"] = amount
        if note is not None:
            payload["note"] = note
        if tag_ids is not None:
            payload["tag_ids"] = tag_ids

        if not payload:
            return "❌ Aucun champ à modifier."

        resp = api.patch(f"/transactions/{transaction_id}", json_data=payload)
        error = handle_response(resp)
        if error:
            return error

        tx = resp.json()
        return f"✅ Transaction #{transaction_id} mise à jour.\nChamps modifiés : {', '.join(payload.keys())}"
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def delete_transaction(transaction_id: int) -> str:
    """Supprime une transaction. ⚠️ Action irréversible !

    Args:
        transaction_id: ID de la transaction à supprimer
    """
    try:
        resp = api.delete(f"/transactions/{transaction_id}")
        if resp.status_code == 204:
            return f"🗑️ Transaction #{transaction_id} supprimée."
        error = handle_response(resp)
        if error:
            return error
        return f"🗑️ Transaction #{transaction_id} supprimée."
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def bulk_update_transactions(
    ids: list[int],
    category_id: int | None = None,
    type: str | None = None,
    merchant: str | None = None,
    tag_ids: list[int] | None = None,
) -> str:
    """Met à jour plusieurs transactions en une fois.

    Args:
        ids: Liste des IDs de transactions à modifier
        category_id: Nouvelle catégorie (optionnel)
        type: Nouveau type (optionnel)
        merchant: Nouveau marchand (optionnel)
        tag_ids: Nouveaux tag IDs (optionnel)
    """
    try:
        payload: dict[str, Any] = {"ids": ids}
        if category_id is not None:
            payload["category_id"] = category_id
        if type is not None:
            payload["type"] = type
        if merchant is not None:
            payload["merchant"] = merchant
        if tag_ids is not None:
            payload["tag_ids"] = tag_ids

        resp = api.patch("/transactions/bulk", json_data=payload)
        if resp.status_code == 204:
            return f"✅ {len(ids)} transaction(s) mise(s) à jour."
        error = handle_response(resp)
        if error:
            return error
        return f"✅ {len(ids)} transaction(s) mise(s) à jour."
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def categorize_transaction(transaction_id: int, category_id: int) -> str:
    """Change la catégorie d'une transaction.

    Args:
        transaction_id: ID de la transaction
        category_id: ID de la nouvelle catégorie
    """
    try:
        resp = api.patch(
            f"/transactions/{transaction_id}",
            json_data={"category_id": category_id}
        )
        error = handle_response(resp)
        if error:
            return error
        tx = resp.json()
        cat_name = tx.get("category", {}).get("name", "?") if tx.get("category") else "?"
        return f"✅ Transaction #{transaction_id} ({tx.get('merchant', '')}) → catégorie '{cat_name}'"
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def bulk_categorize_by_merchant(merchant: str, category_id: int) -> str:
    """Catégorise toutes les transactions d'un marchand donné.

    Args:
        merchant: Nom du marchand (recherche partielle)
        category_id: ID de la catégorie à appliquer
    """
    try:
        # 1. Trouver les transactions de ce marchand
        resp = api.get("/transactions", params={"merchant": merchant, "limit": 1000})
        error = handle_response(resp)
        if error:
            return error
        transactions = resp.json()

        if not transactions:
            return f"❌ Aucune transaction trouvée pour '{merchant}'."

        ids = [tx["id"] for tx in transactions]

        # 2. Bulk update
        resp = api.patch("/transactions/bulk", json_data={
            "ids": ids,
            "category_id": category_id,
        })
        if resp.status_code == 204:
            return f"✅ {len(ids)} transaction(s) de '{merchant}' catégorisée(s)."
        error = handle_response(resp)
        if error:
            return error
        return f"✅ {len(ids)} transaction(s) de '{merchant}' catégorisée(s)."
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def add_category(
    name: str,
    type: str,
    icon: str | None = None,
    color: str | None = None,
    group: str | None = None,
    monthly_limit: float | None = None,
    annual_limit: float | None = None,
) -> str:
    """Ajoute une nouvelle catégorie.

    Args:
        name: Nom de la catégorie
        type: Type (depense ou revenu)
        icon: Nom de l'icône (optionnel)
        color: Couleur hex (optionnel, ex: #FF5733)
        group: Groupe (optionnel, ex: Essentiel, Plaisir, Épargne)
        monthly_limit: Limite budgétaire mensuelle (optionnel)
        annual_limit: Limite budgétaire annuelle (optionnel)
    """
    try:
        payload: dict[str, Any] = {"name": name, "type": type}
        if icon:
            payload["icon"] = icon
        if color:
            payload["color"] = color
        if group:
            payload["group"] = group
        if monthly_limit is not None:
            payload["monthly_limit"] = monthly_limit
        if annual_limit is not None:
            payload["annual_limit"] = annual_limit

        resp = api.post("/categories", json_data=payload)
        error = handle_response(resp)
        if error:
            return error

        cat = resp.json()
        return f"✅ Catégorie '{cat['name']}' créée (ID: #{cat['id']})"
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def add_recurring_transaction(
    account_id: int,
    name: str,
    type: str,
    amount: float,
    frequency: str,
    start_date: str,
    category_id: int | None = None,
    day_of_month: int | None = None,
    note: str | None = None,
) -> str:
    """Ajoute une transaction récurrente (abonnement, salaire, etc.).

    Args:
        account_id: ID du compte
        name: Nom de la récurrence (ex: Netflix, Salaire)
        type: Type (Entree, Sortie, Interets)
        amount: Montant
        frequency: Fréquence (monthly, weekly, quarterly, yearly)
        start_date: Date de début (YYYY-MM-DDTHH:MM:SS)
        category_id: Catégorie (optionnel)
        day_of_month: Jour du mois (1-31, optionnel)
        note: Note (optionnel)
    """
    try:
        if "T" not in start_date:
            start_date = start_date + "T00:00:00"

        payload: dict[str, Any] = {
            "account_id": account_id,
            "name": name,
            "type": type,
            "amount": amount,
            "frequency": frequency,
            "start_date": start_date,
        }
        if category_id is not None:
            payload["category_id"] = category_id
        if day_of_month is not None:
            payload["day_of_month"] = day_of_month
        if note:
            payload["note"] = note

        resp = api.post("/recurring-transactions/", json_data=payload)
        error = handle_response(resp)
        if error:
            return error

        rt = resp.json()
        return (
            f"✅ Récurrence '{rt['name']}' créée (ID: #{rt['id']})\n"
            f"  💰 {rt['amount']} € / {rt['frequency']}\n"
        )
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
    """Aide à catégoriser les transactions sans catégorie."""
    return """Trouve et catégorise les transactions sans catégorie.

Étapes :
1. `list_categories()` — voir les catégories existantes
2. `list_transactions(limit=200)` — chercher les transactions
3. Pour chaque transaction sans catégorie, propose une catégorie
4. Demande confirmation avant d'appliquer
5. Utilise `categorize_transaction()` ou `bulk_categorize_by_merchant()` pour appliquer

Groupe les transactions par marchand pour être efficace.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Point d'entrée
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info(f"Démarrage du serveur MCP '{SERVER_NAME}' v{__version__}")
    logger.info(f"API cible : {API_BASE_URL}")
    logger.info(f"Transport : {TRANSPORT}")

    if TRANSPORT == "streamable-http":
        logger.info(f"Écoute sur {HOST}:{PORT}")
        mcp.run(transport="streamable-http", host=HOST, port=PORT)
    elif TRANSPORT == "sse":
        logger.info(f"Écoute sur {HOST}:{PORT}")
        mcp.run(transport="sse", host=HOST, port=PORT)
    else:
        mcp.run(transport="stdio")
