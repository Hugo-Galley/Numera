"""Notifications push : alertes du Centre d'Actions et résumé hebdomadaire vers ntfy et/ou Telegram.

Appelé par la tâche de fond horaire (`main.py`). Règles :
- une alerte (empreinte = id + titre + description) n'est envoyée qu'une fois ; si son texte change
  (budget 80 % → 100 %), l'empreinte change et elle repart ;
- première activation : les alertes déjà présentes sont marquées connues et un seul message de bienvenue part ;
- plus de `GROUP_THRESHOLD` nouvelles alertes d'un coup → un seul message groupé ;
- un canal en échec n'empêche ni les autres ni la tâche ; rien n'est marqué envoyé si aucun canal n'a reçu ;
- résumé le dimanche, au premier passage après `DIGEST_HOUR` (heure locale du serveur), une fois par semaine ISO.
Seuls appels sortants : le serveur ntfy configuré et `api.telegram.org`, choisis par l'utilisateur.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import ExternalServiceError, InvalidOperationError
from app.core.logging import get_logger
from app.db.system_settings import get_setting, set_setting
from app.integrations.notifications import DEFAULT_NTFY_SERVER, Channel, NtfyChannel, TelegramChannel, send_all
from app.models.notification_log import NotificationLog
from app.schemas.insight import ActionItem
from app.services.analytics.budget import compute_budget
from app.services.analytics.reports import compute_cashflow_projection
from app.services.audit import compute_action_center

logger = get_logger(__name__)

SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}
GROUP_THRESHOLD = 5
DIGEST_WEEKDAY = 6  # dimanche
DIGEST_HOUR = 18

KEYS = {
    "ntfy_enabled": "notify.ntfy.enabled",
    "ntfy_server": "notify.ntfy.server",
    "ntfy_topic": "notify.ntfy.topic",
    "ntfy_token": "notify.ntfy.token",
    "telegram_enabled": "notify.telegram.enabled",
    "telegram_bot_token": "notify.telegram.bot_token",
    "telegram_chat_id": "notify.telegram.chat_id",
    "min_severity": "notify.min_severity",
    "weekly_digest": "notify.weekly_digest",
    "hide_amounts": "notify.hide_amounts",
    "public_url": "notify.public_url",
}
SECRET_FIELDS = ("ntfy_token", "telegram_bot_token")
BOOL_FIELDS = ("ntfy_enabled", "telegram_enabled", "weekly_digest", "hide_amounts")
INITIALIZED_KEY = "notify.initialized"
LAST_DIGEST_KEY = "notify.last_digest_week"


@dataclass(frozen=True)
class NotificationSettings:
    ntfy_enabled: bool = False
    ntfy_server: str = DEFAULT_NTFY_SERVER
    ntfy_topic: str = ""
    ntfy_token: str = ""
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    min_severity: str = "medium"
    weekly_digest: bool = False
    hide_amounts: bool = False
    public_url: str = ""


def load_settings(db: Session) -> NotificationSettings:
    defaults = NotificationSettings()
    values: dict = {}
    for field, key in KEYS.items():
        raw = get_setting(db, key)
        if raw is None or raw == "":
            values[field] = getattr(defaults, field)
        elif field in BOOL_FIELDS:
            values[field] = raw == "1"
        else:
            values[field] = raw
    if values["min_severity"] not in SEVERITY_RANK:
        values["min_severity"] = defaults.min_severity
    return NotificationSettings(**values)


def mask_secret(value: str) -> str:
    return f"••••{value[-4:]}" if value else ""


def save_settings(db: Session, update: dict) -> NotificationSettings:
    """Enregistre les champs fournis ; un jeton renvoyé masqué (`••••xxxx`) garde sa valeur."""
    current = load_settings(db)
    for field, value in update.items():
        if field not in KEYS or value is None:
            continue
        if field in SECRET_FIELDS and value == mask_secret(getattr(current, field)) and value:
            continue
        stored = ("1" if value else "0") if field in BOOL_FIELDS else str(value).strip()
        set_setting(db, KEYS[field], stored)
    return load_settings(db)


def build_channel(db: Session, name: str) -> Channel | None:
    """Canal configuré (activé ou non), ou None s'il manque un paramètre obligatoire."""
    settings = load_settings(db)
    if name == "ntfy" and settings.ntfy_topic:
        return NtfyChannel(settings.ntfy_server, settings.ntfy_topic, settings.ntfy_token or None)
    if name == "telegram" and settings.telegram_bot_token and settings.telegram_chat_id:
        return TelegramChannel(settings.telegram_bot_token, settings.telegram_chat_id)
    return None


def enabled_channels(db: Session) -> list[Channel]:
    settings = load_settings(db)
    names = [name for name, on in (("ntfy", settings.ntfy_enabled), ("telegram", settings.telegram_enabled)) if on]
    return [channel for name in names if (channel := build_channel(db, name))]


_AMOUNT = re.compile(r"\d{1,3}(?:[   .]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?(?=\s?(?:€|EUR|\$|£|CHF))")


def mask_amounts(text: str) -> str:
    """Remplace les montants (suivis d'une devise, ou à séparateur de milliers) par « ••• »."""
    return _AMOUNT.sub("•••", text)


def fingerprint(action: ActionItem) -> str:
    return hashlib.sha256(f"{action.id}|{action.title}|{action.description}".encode()).hexdigest()


async def current_actions(db: Session) -> list[ActionItem]:
    return (await compute_action_center(db=db)).actions


def _link(settings: NotificationSettings, path: str | None) -> str | None:
    if not settings.public_url or not path:
        return None
    return settings.public_url.rstrip("/") + "/" + path.lstrip("/")


def _log(db: Session, items: list[tuple[str, str]], channel: str) -> None:
    for print_, action_id in items:
        db.add(NotificationLog(fingerprint=print_, action_id=action_id[:120], channel=channel[:32]))
    db.commit()


async def run_notifications(db: Session, now: datetime | None = None) -> int:
    """Envoie les nouvelles alertes (et le résumé hebdo s'il est dû). Renvoie le nombre de messages envoyés."""
    now = now or datetime.now()
    channels = enabled_channels(db)
    if not channels:
        return 0
    settings = load_settings(db)
    clean = mask_amounts if settings.hide_amounts else (lambda text: text)
    floor = SEVERITY_RANK[settings.min_severity]
    actions = [a for a in await current_actions(db) if SEVERITY_RANK.get(a.severity, 0) >= floor]
    known = {row.fingerprint for row in db.query(NotificationLog.fingerprint).all()}
    fresh = [(fingerprint(a), a) for a in actions if fingerprint(a) not in known]
    sent = 0

    if get_setting(db, INITIALIZED_KEY) != "1":
        body = f"Notifications activées : {len(actions)} action(s) en cours dans le Centre d'Actions."
        if await send_all(channels, "Numera connecté", body, "default", _link(settings, "/audit")):
            _log(db, [(p, a.id) for p, a in fresh], "init")
            set_setting(db, INITIALIZED_KEY, "1")
            sent += 1
        return sent

    if len(fresh) > GROUP_THRESHOLD:
        top = max(fresh, key=lambda item: SEVERITY_RANK.get(item[1].severity, 0))[1]
        body = "\n".join(f"• {clean(a.title)}" for _, a in fresh)
        delivered = await send_all(channels, f"{len(fresh)} nouvelles alertes Numera", body, top.severity, _link(settings, "/audit"))
        if delivered:
            _log(db, [(p, a.id) for p, a in fresh], ",".join(delivered))
            sent += 1
    else:
        for print_, action in fresh:
            delivered = await send_all(
                channels, clean(action.title), clean(action.description), action.severity,
                _link(settings, action.action_url or "/audit"),
            )
            if delivered:
                _log(db, [(print_, action.id)], ",".join(delivered))
                sent += 1

    if await send_weekly_digest(db, now):
        sent += 1
    return sent


def _eur(value: float) -> str:
    return f"{value:,.2f}".replace(",", "\u202f").replace(".", ",") + " €"


def _week_key(now: datetime) -> str:
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


async def _digest_body(db: Session, now: datetime) -> str:
    lines: list[str] = []
    try:
        budget = await compute_budget(month=now.month, year=now.year, account_id=None, db=db)
        lines.append(f"Ce mois-ci : {_eur(budget['depenses_reelles'])} de dépenses réelles, {_eur(budget['revenus_totaux'])} de revenus.")
    except Exception as exc:
        logger.warning(f"Digest budget skipped: {exc}")
    try:
        actions = await current_actions(db)
        urgent = sum(1 for a in actions if a.severity == "high")
        lines.append(f"Centre d'Actions : {len(actions)} action(s) en cours, dont {urgent} urgente(s).")
    except Exception as exc:
        logger.warning(f"Digest actions skipped: {exc}")
    try:
        projection = await compute_cashflow_projection(days=7, account_id=None, db=db)
        limit = (now + timedelta(days=7)).date().isoformat()
        upcoming = [e for e in projection.events if e.date[:10] <= limit][:5]
        if upcoming:
            lines.append("Échéances des 7 prochains jours :")
            lines += [f"• {e.date[:10]} {e.name} : {'+' if e.is_income else '−'}{_eur(e.amount)}" for e in upcoming]
    except Exception as exc:
        logger.warning(f"Digest projection skipped: {exc}")
    return "\n".join(lines) or "Rien de particulier cette semaine."


async def send_weekly_digest(db: Session, now: datetime) -> bool:
    settings = load_settings(db)
    if not settings.weekly_digest or now.weekday() != DIGEST_WEEKDAY or now.hour < DIGEST_HOUR:
        return False
    week = _week_key(now)
    if get_setting(db, LAST_DIGEST_KEY) == week:
        return False
    channels = enabled_channels(db)
    if not channels:
        return False
    body = await _digest_body(db, now)
    if settings.hide_amounts:
        body = mask_amounts(body)
    if not await send_all(channels, "Ta semaine avec Numera", body, "low", _link(settings, "/")):
        return False
    set_setting(db, LAST_DIGEST_KEY, week)
    return True


def masked_settings(settings: NotificationSettings) -> dict:
    """Réglages lisibles par le client : jetons masqués (•••• + 4 derniers caractères)."""
    data = asdict(settings)
    for field in SECRET_FIELDS:
        data[field] = mask_secret(data[field])
    return data


def get_notification_settings(db: Session) -> dict:
    return masked_settings(load_settings(db))


def update_notification_settings(db: Session, update: dict) -> dict:
    return masked_settings(save_settings(db, update))


async def send_test_notification(db: Session, payload) -> dict:
    """Message d'essai sur un canal configuré, même désactivé (pour valider les réglages avant de l'activer)."""
    channel = build_channel(db, payload.channel)
    if channel is None:
        raise InvalidOperationError("Canal incomplet : renseignez ses paramètres puis enregistrez.")
    delivered = await send_all([channel], "Test Numera", "Les notifications fonctionnent.", "default")
    if not delivered:
        raise ExternalServiceError("Envoi impossible : vérifiez l'adresse, le sujet ou le jeton.")
    return {"channel": payload.channel, "delivered": True}
