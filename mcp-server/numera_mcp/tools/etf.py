"""Outils MCP investissement : profils ETF et scanner de diversification."""

from typing import Any

from numera_mcp.api_client import api, handle_response
from numera_mcp.formatting import format_table


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


def _format_diversity(data: dict) -> str:
    """Texte du scanner de diversification à partir de la réponse de l'API."""
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

        return _format_diversity(data)
    except Exception as e:
        return f"❌ Erreur : {e}"


TOOLS = [
    list_etf_profiles,
    get_etf_profile,
    get_diversity_scanner,
]


def register(mcp) -> None:
    for tool in TOOLS:
        mcp.tool()(tool)
