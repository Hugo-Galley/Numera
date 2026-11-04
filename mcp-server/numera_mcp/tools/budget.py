"""Outils MCP du domaine budget (transactions, catégories, marchands, récurrences, remboursements, revue de mois)."""

from typing import Any

from numera_mcp.api_client import api, handle_response
from numera_mcp.formatting import format_table, serialize


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


TOOLS = [
    list_categories,
    list_transactions,
    get_transaction,
    search_transactions,
    list_merchants,
    list_recurring_transactions,
    list_tags,
]


def register(mcp) -> None:
    for tool in TOOLS:
        mcp.tool()(tool)
