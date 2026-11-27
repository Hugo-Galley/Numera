"""Outils MCP investissement : profils ETF et scanner de diversification."""

from typing import Any

from numera_mcp.api_client import api, handle_response
from numera_mcp.formatting import format_table

SOURCE_LABELS = {"ishares": "iShares", "amundi": "Amundi", "spdr": "SPDR", "justetf": "justETF",
                 "yahoo": "Yahoo Finance", "manual": "saisie manuelle"}
REPLICATION_LABELS = {"physical": "physique", "synthetic": "synthétique", "unknown": "inconnue"}


def _replication(p: dict) -> str:
    label = REPLICATION_LABELS.get(p.get("replication") or "unknown", "inconnue")
    if p.get("replication") == "synthetic" and p.get("exposure_profile_name"):
        label += f" via {p['exposure_profile_name']}"
    return label


def _coverage(p: dict) -> str:
    return f"{p['coverage_pct']} %" if p.get("coverage_pct") is not None else "—"


def list_etf_profiles() -> str:
    """Liste tous les profils ETF connus avec leur composition par pays, secteurs et top holdings.

    Utile pour comprendre ce que contient réellement un ETF.
    Aucun profil n'est livré avec Numera : chaque fonds détenu a le sien, retrouvé par son ISIN.
    La composition est lue chaque jour chez l'émetteur (iShares, Amundi, SPDR ; à défaut justETF
    puis Yahoo, partiels) ou saisie à la main. Un champ inconnu reste vide. Un ETF synthétique
    n'a pas de chiffres propres : son exposition est celle d'un ETF physique du même indice
    (colonne exposition_via, chiffres par get_etf_profile).
    Colonnes : source et date publiée de la composition, part du fonds décrite (couverture).
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
                "replication": REPLICATION_LABELS.get(p.get("replication") or "unknown", "inconnue"),
                "exposition_via": (p.get("exposure_profile_name") or "—") if p.get("replication") == "synthetic" else "—",
                "source": SOURCE_LABELS.get(p.get("provider") or "", "—"),
                "date": p.get("composition_as_of") or "—",
                "couverture": _coverage(p),
                "top_pays": top_countries,
                "top_holdings": top_names,
            })
        return f"🗂️ {len(simplified)} profil(s) ETF :\n\n" + format_table(simplified)
    except Exception as e:
        return f"❌ Erreur : {e}"


def _origin_lines(p: dict) -> list[str]:
    """Réplication, indice, source, date publiée, lignes et couverture de la composition."""
    index = f" (indice {p['index_name']})" if p.get("index_name") else ""
    source = SOURCE_LABELS.get(p.get("provider") or "", "aucune")
    dated = f"composition au {p['composition_as_of']}" if p.get("composition_as_of") else "date non publiée"
    lines = f"{p['lines_count']} lignes" if p.get("lines_count") else "agrégats seulement"
    return [
        f"   Réplication : {_replication(p)}{index}",
        f"   Composition : {source} · {dated} · {lines} · couverture {_coverage(p)}",
    ]


def _breakdown_lines(data: dict) -> list[str]:
    lines: list[str] = []
    for key, title in (("countries", "🌍 Pays :"), ("sectors", "🏭 Secteurs :")):
        values = data.get(key) or {}
        if values:
            lines.append(title)
            for name, pct in sorted(values.items(), key=lambda x: -float(x[1]))[:10]:
                lines.append(f"  • {name} : {pct}%")
            lines.append("")
    top_holdings = data.get("top_holdings") or []
    if top_holdings:
        lines.append("🏢 Top Holdings :")
        for h in top_holdings[:10]:
            ticker_str = f" ({h.get('ticker')})" if h.get("ticker") else ""
            lines.append(f"  • {h.get('name', '')}{ticker_str} : {h.get('weight', 0)}%")
    return lines


def _exposure_lines(data: dict) -> list[str]:
    """Synthétique : son panier détenu ne dit rien de son exposition, celle de l'ETF de référence de l'indice."""
    if data.get("replication") != "synthetic":
        return []
    if not data.get("exposure_profile_id"):
        return ["⚠️ Synthétique : indice non reconnu, exposition indisponible."]
    resp = api.get(f"/etf-profiles/{data['exposure_profile_id']}")
    error = handle_response(resp)
    if error:
        return [f"⚠️ Exposition via {data.get('exposure_profile_name') or 'la référence'} illisible : {error}"]
    reference = resp.json()
    return [
        f"🔁 Exposition de l'indice {data.get('index_name') or '?'} via {reference.get('name', '')} "
        f"({reference.get('isin') or '—'}) :",
        *_origin_lines(reference),
        "",
        *_breakdown_lines(reference),
    ]


def get_etf_profile(profile_id: int) -> str:
    """Récupère le détail complet d'un profil ETF : pays (%), secteurs (%) et top 10 positions.

    Les sources de chaque champ sont indiquées (émetteur, justETF, Yahoo Finance ou saisie manuelle),
    avec la réplication, l'indice, la date publiée de la composition, le nombre de lignes et la
    couverture. Pour un ETF synthétique, l'exposition est celle de l'ETF physique de référence du même
    indice : ses chiffres sont lus et affichés.

    Args:
        profile_id: ID du profil ETF (obtenir via list_etf_profiles)
    """
    try:
        resp = api.get(f"/etf-profiles/{profile_id}")
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        sources = data.get("composition_sources") or {}
        lines = [
            f"🗂️ ETF : {data.get('name', '')} ({data.get('ticker', '')})",
            f"   ISIN : {data.get('isin') or '—'}",
            *_origin_lines(data),
            "   Sources : " + ", ".join(
                f"{label} = {SOURCE_LABELS.get(sources.get(field), 'non renseigné')}"
                for field, label in (("countries", "pays"), ("sectors", "secteurs"), ("top_holdings", "top 10"))
            ),
            f"   Actualisé le : {data.get('composition_refreshed_at') or 'jamais'}",
            "",
            *_breakdown_lines(data),
        ]
        exposure = _exposure_lines(data)
        if exposure:
            lines += ["", *exposure]
        return "\n".join(lines).rstrip()
    except Exception as e:
        return f"❌ Erreur : {e}"


def _line_rows(lines: list[dict]) -> list[dict]:
    """Un top 10 saisi à la main peut manquer de nom ou de poids : la ligne reste affichée."""
    return [{"société": x.get("name") or "—", "ticker": x.get("ticker") or "—", "isin": x.get("isin") or "—",
             "pays": x.get("country") or "—", "secteur": x.get("sector") or "—", "poids": f"{x.get('weight', 0)} %",
             "exposition": f"{x.get('exposure_eur') or 0:,.2f} €"}
            for x in lines]


def _sheet_header(sheet: dict) -> list[str]:
    profile = sheet["profile"]
    source = SOURCE_LABELS.get(sheet.get("provider") or "", "aucune")
    dated = f"composition au {sheet['composition_as_of']}" if sheet.get("composition_as_of") else "date non publiée"
    lines = [
        f"🗂️ ETF : {profile.get('name', '')} ({profile.get('ticker', '')})",
        f"   ISIN : {profile.get('isin') or '—'}",
        f"   Composition : {source} · {dated} · couverture {_coverage(sheet)}",
        f"   Détenu : {sheet.get('held_value_eur', 0):,.2f} €",
    ]
    if sheet.get("exposure_profile_name"):
        lines.append(f"🔁 Exposition de l'indice {profile.get('index_name') or '?'} via {sheet['exposure_profile_name']}")
    return lines


def _matches(line: dict, needle: str) -> bool:
    return any(needle in (line.get(key) or "").lower() for key in ("name", "ticker", "isin"))


def get_etf_constituents(profile_id: int, limit: int = 50, search: str | None = None) -> str:
    """Liste les sociétés contenues dans un ETF (toutes les lignes publiées, de la plus lourde à la plus légère).

    Affiche aussi l'identité du fonds, la source, la date et la couverture de la composition, la valeur
    détenue et l'exposition en € de chaque ligne (poids × valeur détenue, calculée par le backend). Pour un ETF synthétique, les lignes sont celles de l'ETF physique de référence du même indice.
    Sans liste complète (certaines sources ne publient que les principales lignes), seules celles-ci sont données.

    Args:
        profile_id: ID du profil ETF (obtenir via list_etf_profiles)
        limit: Nombre maximal de lignes affichées (défaut 50)
        search: Filtre sur le nom, le ticker ou l'ISIN d'une société (optionnel)
    """
    try:
        resp = api.get(f"/etf-profiles/{profile_id}/constituents")
        error = handle_response(resp)
        if error:
            return error
        sheet = resp.json()
        complete = sheet.get("has_full_list")
        lines = sheet["lines"] if complete else [
            {**h, "sector": None} for h in sheet.get("top_holdings") or []
        ]
        if search:
            lines = [x for x in lines if _matches(x, search.strip().lower())]
        text = _sheet_header(sheet)
        if not complete:
            text.append("⚠️ Seules les principales lignes sont connues : liste complète indisponible.")
        total = f"{len(sheet['lines'])} lignes au total" if complete else f"{len(sheet.get('top_holdings') or [])} lignes connues"
        found = f"{len(lines)} ligne{'s' if len(lines) > 1 else ''} trouvée{'s' if len(lines) > 1 else ''} · " if search else ""
        shown = lines[:max(limit, 0)]
        text += ["", f"🏢 {found}{total} ({len(shown)} affichées) :", format_table(_line_rows(shown))]
        return "\n".join(text)
    except Exception as e:
        return f"❌ Erreur : {e}"


def _format_market(data: dict) -> list[str]:
    """Référence de marché, active share par dimension et principaux écarts de secteurs et de pays."""
    market = data.get("market")
    if market is None:
        return ["📏 Référence de marché indisponible : score neutre, pas d'écart au marché.", ""]
    ticker = f" ({market['ticker']})" if market.get("ticker") else ""
    lines = [f"📏 Référence de marché : {market['name']}{ticker} — score = 100 − active share moyenne"]
    for key, label in (("companies", "sociétés"), ("sectors", "secteurs"), ("countries", "pays")):
        dimension = market.get(key) or {}
        if dimension.get("comparable") is False:
            lines.append(f"  • {label.capitalize()} : rien de comparable (données absentes d'un côté)")
            continue
        lines.append(f"  • Active share {label} : {dimension.get('active_share_pct', 0)}% "
                     f"(part comparée {dimension.get('covered_pct', 0)}%)")
    for key in ("sectors", "countries"):
        for row in (market.get(key) or {}).get("rows", [])[:5]:
            bound = "≤ " if row.get("market_pct_is_upper_bound") else ""
            lines.append(f"    {row['name']} : {row['portfolio_pct']}% contre {bound}{row['market_pct']}% "
                         f"({row['gap_pts']:+} pts)")
    return [*lines, ""]


def _format_concentration(data: dict) -> list[str]:
    """Paris indépendants, blocs corrélés, expositions à plusieurs supports et stock picking."""
    lines: list[str] = []
    concentration = data.get("concentration")
    if concentration:
        lines.append(f"🧮 {concentration['effective_bets']} paris indépendants sur "
                     f"{concentration['exposures_count']} lignes")
        for block in concentration.get("blocks", []):
            lines.append(f"  • Bloc corrélé : {' + '.join(block['members'])} — {block['weight_pct']}% "
                         f"(ρ moyen {block['mean_rho']})")
    for exposure in data.get("exposures", []):
        supports = exposure.get("supports", [])
        if len(supports) > 1:
            where = ", ".join(f"{s.get('account_name') or s['ticker']} {s['value_eur']:,.2f} €" for s in supports)
            lines.append(f"  • {exposure['name']} : une seule exposition sur {len(supports)} supports ({where})")
    for pick in data.get("stock_picking", []):
        rho = pick.get("correlation_with_core")
        verdict = " — redondant" if pick.get("redundant") else ""
        lines.append(f"  • {pick['name']} en direct : {pick['indirect_value_eur']:,.2f} € déjà via tes fonds, "
                     f"ρ avec le cœur {rho if rho is not None else 'inconnu'} ({pick['source']}){verdict}")
    coverage = data.get("coverage")
    if coverage:
        lines.append(f"  Couverture : composition {coverage.get('composition_pct', 0)}%, "
                     f"historique de cours {coverage.get('with_prices_pct', 0)}% de la valeur")
    return [*lines, ""] if lines else []


def _format_diversity(data: dict) -> str:
    """Texte du scanner de diversification à partir de la réponse de l'API."""
    lines = [
        f"🎯 Score de diversité : {data.get('score', '—')}/100 — {data.get('score_label', '')}",
        "",
        *_format_market(data),
        *_format_concentration(data),
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
            overlap = " 🔁 doublon (plusieurs chemins)" if c.get("has_overlap") else ""
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
    get_etf_constituents,
    get_diversity_scanner,
]


def register(mcp) -> None:
    for tool in TOOLS:
        mcp.tool()(tool)
