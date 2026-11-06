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


def trn(key: str, count: int, **params: Any) -> str:
    """Texte avec pluriel : `key_one` ou `key_other` (le français compte 0 et 1 au singulier), `{count}` fourni."""
    one = count == 1 or (get_language() == "fr" and count == 0)
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
