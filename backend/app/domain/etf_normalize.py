"""Normalisation des libellés de composition d'ETF (pays, secteurs, classes d'actifs).

Chaque émetteur (iShares, Amundi, SPDR, justETF) et Yahoo publient leurs propres libellés ;
on les ramène ici à un vocabulaire unique : pays en ISO 3166-1 alpha-3 (convention du frontend),
secteurs en libellés français de l'application. Fonctions pures, sans accès base ni réseau.
Les libellés sont comparés sans casse, sans accents ni ponctuation.
"""

import json
import re
import unicodedata
from pathlib import Path

UNKNOWN_LABEL = "Non renseigné"

_COUNTRIES: dict[str, dict[str, list[str]]] = json.loads(Path(__file__).with_name("country_codes.json").read_text(encoding="utf-8"))

# Sources : GICS (iShares, Amundi, SPDR), assetProfile et clés topHoldings de Yahoo, justETF (français).
_SECTOR_ALIASES: dict[str, tuple[str, ...]] = {
    "Technologie": ("information technology", "technology", "technologie", "technologies de l information"),
    "Finance": ("financials", "financial", "financial services", "finance", "services financiers"),
    "Santé": ("health care", "healthcare", "sante", "soins de sante"),
    "Industrie": ("industrials", "industrial", "industrie", "industries"),
    "Consommation discrétionnaire": (
        "consumer discretionary",
        "consumer cyclical",
        "consommation discretionnaire",
        "consommation cyclique",
    ),
    "Biens de consommation": (
        "consumer staples",
        "consumer defensive",
        "biens de consommation",
        "biens de consommation de base",
        "consommation de base",
        "consommation defensive",
    ),
    "Services de communication": (
        "communication",
        "communications",
        "communication services",
        "services de communication",
        "telecommunications",
        "telecommunication services",
        "telecom",
    ),
    "Énergie": ("energy", "energie"),
    "Matériaux": ("materials", "basic materials", "materiaux", "materiaux de base", "matieres premieres"),
    "Services aux collectivités": ("utilities", "services aux collectivites", "services publics"),
    "Immobilier": ("real estate", "realestate", "immobilier"),
}
_SECTORS: dict[str, str] = {alias: label for label, aliases in _SECTOR_ALIASES.items() for alias in aliases}

# Séquences de mots (sans accents) qui désignent une ligne qui n'est pas une action. Comparées mot entier par mot entier.
_NON_EQUITY_PHRASES: tuple[tuple[str, ...], ...] = tuple(
    tuple(p.split())
    for p in (
        "cash",
        "cash collateral",
        "collateral",
        "liquidity",
        "ndf",
        "non deliverable forward",
        "money market",
        "futures",
        "future",
        "fx",
        "fx forward",
        "forwards",
        "swap",
        "swaps",
        "margin",
        "margins",
        "repo",
        "currency",
        "currencies",
        "derivative",
        "derivatives",
        "liquidites",
        "tresorerie",
        "derives",
        "contrats a terme",
        "marche monetaire",
    )
)


def _key(label: str | None) -> str:
    """Clé de comparaison : sans accents, minuscules, ponctuation et tirets ramenés à des espaces."""
    if not label:
        return ""
    decomposed = unicodedata.normalize("NFKD", label)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", ascii_only).split())


_COUNTRY_BY_KEY: dict[str, str] = {
    _key(name): code for code, names in _COUNTRIES.items() for name in (*names["en"], *names["fr"], code)
}


def country_code(label: str | None) -> str | None:
    """Code ISO alpha-3 d'un libellé de pays (anglais, français ou variante d'émetteur) ; `None` si inconnu (« Other », « Autre »…)."""
    return _COUNTRY_BY_KEY.get(_key(label))


def sector_label(label: str | None) -> str:
    """Libellé de secteur français de l'application ; `« Non renseigné »` si le secteur est inconnu."""
    return _SECTORS.get(_key(label), UNKNOWN_LABEL)


def _has_phrase(tokens: list[str], phrase: tuple[str, ...]) -> bool:
    size = len(phrase)
    return any(tuple(tokens[i : i + size]) == phrase for i in range(len(tokens) - size + 1))


def _is_equity_wording(tokens: list[str]) -> bool:
    return bool({"equity", "equities", "action", "actions"}.intersection(tokens))


def is_equity_line(asset_class: str | None, type_: str | None) -> bool:
    """Faux pour les lignes de liquidités, monétaire, futures, change, swaps, collatéral, dérivés ; vrai sinon.

    Les mots sont comparés entiers (« Cashflow Growth » reste une action). Les obligations (« Bonds », « Fixed Income »)
    restent vraies : ce sont des lignes investies, pas des liquidités. Sans information, vrai.
    """
    for value in (asset_class, type_):
        tokens = _key(value).split()
        if not ({"forward", "forwards"}.isdisjoint(tokens) or _is_equity_wording(tokens)):
            return False
        if any(_has_phrase(tokens, phrase) for phrase in _NON_EQUITY_PHRASES):
            return False
    return True
