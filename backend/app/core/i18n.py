"""Textes du backend dans la langue de l'interface.

La langue vient de l'en-tête `Accept-Language` (le frontend envoie celle choisie dans Paramètres) ;
sans en-tête, ou pour une langue inconnue : français, la langue de référence. Les clients sans
interface (serveur MCP, scripts) restent donc en français, comme avant.

Les textes vivent dans `core/locales/<langue>.json` (clés plates `domaine.sujet`, variables `{nom}`) ;
`tr("clé", nom=valeur)` lit la langue de la requête en cours. Une clé inconnue est rendue telle quelle
(un texte manquant ne casse pas une réponse) ; `tests/systeme/test_i18n.py` impose les mêmes clés et
les mêmes variables en français et en anglais.
"""
import json
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date, datetime
from functools import cache
from pathlib import Path
from typing import Any

LANGUAGES = ("fr", "en")
DEFAULT_LANGUAGE = "fr"
_LOCALES_DIR = Path(__file__).parent / "locales"

_language: ContextVar[str] = ContextVar("language", default=DEFAULT_LANGUAGE)


@cache
def load_catalog(language: str) -> dict[str, str]:
    """Catalogue d'une langue (mis en cache : le dictionnaire rendu est partagé, ne pas le modifier)."""
    catalog: dict[str, str] = json.loads((_LOCALES_DIR / f"{language}.json").read_text(encoding="utf-8"))
    return catalog


def parse_language(header: str | None) -> str:
    """Langue prise en charge d'un en-tête `Accept-Language` (première langue citée), sinon le français."""
    if not header:
        return DEFAULT_LANGUAGE
    first = header.split(",")[0].split(";")[0].strip().lower()
    code = first.split("-")[0]
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


def get_language() -> str:
    return _language.get()


def set_language(language: str) -> None:
    """Fixe la langue du contexte courant (requête, tâche de fond) ; une langue inconnue donne le français."""
    _language.set(language if language in LANGUAGES else DEFAULT_LANGUAGE)


def tr(key: str, **params: Any) -> str:
    """Texte `key` dans la langue courante, variables `{nom}` remplacées ; repli français puis la clé."""
    text = load_catalog(get_language()).get(key)
    if text is None:
        text = load_catalog(DEFAULT_LANGUAGE).get(key, key)
    return text.format(**params) if params else text


@dataclass(frozen=True)
class Formats:
    """Conventions d'une langue pour les nombres, montants, dates et pluriels dans les textes."""

    decimal: str  # séparateur décimal
    thousands: str  # séparateur de milliers (fine insécable en français)
    thousands_plain: str  # variante « espace ordinaire » (messages où l'insécable gênerait)
    symbol_first: bool  # « €1,234.56 » (True) ou « 1 234,56 € » (False)
    symbol_gap: str  # espace entre nombre et symbole quand le symbole suit
    date: str  # format strftime d'une date
    datetime: str  # format strftime d'une date et heure
    zero_is_singular: bool  # « 0 action » au singulier (français) ou au pluriel (anglais)


# Ajouter une langue : une entrée ici, son catalogue `locales/<code>.json`, et son code dans LANGUAGES.
FORMATS: dict[str, Formats] = {
    "fr": Formats(",", "\u202f", " ", False, "\u00a0", "%d/%m/%Y", "%d/%m/%Y %H:%M", True),
    "en": Formats(".", ",", ",", True, "", "%Y-%m-%d", "%Y-%m-%d %H:%M", False),
}


def formats() -> Formats:
    """Conventions de la langue courante."""
    return FORMATS[get_language()]


def format_number(value: float, decimals: int = 2, thousands: str | None = None) -> str:
    """Nombre au format de la langue courante ; `thousands` remplace le séparateur de milliers (« » : aucun)."""
    fmt = formats()
    sep = fmt.thousands if thousands is None else thousands
    table: dict[str, str | int | None] = {",": sep, ".": fmt.decimal}
    return f"{value:,.{decimals}f}".translate(str.maketrans(table))


def format_money(value: float, symbol: str = "€", gap: str | None = None) -> str:
    """Montant avec symbole : « 1 234,56 € » en français, « €1,234.56 » en anglais (`gap` : espace avant le symbole)."""
    fmt = formats()
    number = format_number(value)
    if fmt.symbol_first:
        return f"{symbol}{number}"
    return f"{number}{fmt.symbol_gap if gap is None else gap}{symbol}"


def format_date(value: date) -> str:
    return value.strftime(formats().date)


def format_datetime(value: datetime) -> str:
    return value.strftime(formats().datetime)


def trn(key: str, count: int, **params: Any) -> str:
    """Texte avec pluriel : `key_one` ou `key_other` (le français compte 0 et 1 au singulier), `{count}` fourni."""
    one = count == 1 or (formats().zero_is_singular and count == 0)
    return tr(f"{key}_{'one' if one else 'other'}", count=count, **params)


class LanguageMiddleware:
    """Middleware ASGI : pose la langue de la requête (`Accept-Language`) pour la durée de son traitement."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        header = next((v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"accept-language"), None)
        token = _language.set(parse_language(header))
        try:
            await self.app(scope, receive, send)
        finally:
            _language.reset(token)
