"""Ressources MCP : données consultables par le LLM."""


from numera_mcp.api_client import api, handle_response
from numera_mcp.formatting import serialize


def resource_accounts() -> str:
    """Liste tous les comptes bancaires."""
    resp = api.get("/accounts")
    error = handle_response(resp, "comptes")
    if error:
        return error
    return serialize(resp.json())


def resource_categories() -> str:
    """Liste toutes les catégories."""
    resp = api.get("/categories")
    error = handle_response(resp)
    if error:
        return error
    return serialize(resp.json())


def resource_tags() -> str:
    """Liste tous les tags."""
    resp = api.get("/tags")
    error = handle_response(resp)
    if error:
        return error
    return serialize(resp.json())


def resource_recurring() -> str:
    """Liste toutes les transactions récurrentes (abonnements)."""
    resp = api.get("/recurring-transactions/")
    error = handle_response(resp)
    if error:
        return error
    return serialize(resp.json())


RESOURCES = {
    'data://accounts': resource_accounts,
    'data://categories': resource_categories,
    'data://tags': resource_tags,
    'data://recurring-transactions': resource_recurring,
}


def register(mcp) -> None:
    for uri, resource in RESOURCES.items():
        mcp.resource(uri)(resource)
