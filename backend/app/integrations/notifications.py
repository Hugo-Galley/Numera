"""Canaux d'envoi des notifications push : ntfy (serveur choisi par l'utilisateur) et Telegram.

Seuls appels sortants de ce module : le serveur ntfy configuré et `api.telegram.org`.
"""
from __future__ import annotations

from typing import Protocol

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_NTFY_SERVER = "https://ntfy.sh"
HTTP_TIMEOUT_S = 10.0
NTFY_PRIORITY = {"low": 2, "default": 3, "medium": 3, "high": 4}


class Channel(Protocol):
    name: str

    async def send(self, title: str, body: str, priority: str = "default", url: str | None = None) -> None: ...


class NtfyChannel:
    """Publication JSON sur la racine du serveur (UTF-8 sans souci, contrairement aux en-têtes HTTP)."""

    name = "ntfy"

    def __init__(self, server: str, topic: str, token: str | None, transport: httpx.AsyncBaseTransport | None = None):
        self.server = (server or DEFAULT_NTFY_SERVER).rstrip("/") + "/"
        self.topic = topic
        self.token = token
        self.transport = transport

    async def send(self, title: str, body: str, priority: str = "default", url: str | None = None) -> None:
        payload: dict = {"topic": self.topic, "title": title, "message": body, "priority": NTFY_PRIORITY.get(priority, 3)}
        if url:
            payload["click"] = url
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S, transport=self.transport) as client:
            response = await client.post(self.server, json=payload, headers=headers)
            response.raise_for_status()


class TelegramChannel:
    name = "telegram"

    def __init__(self, bot_token: str, chat_id: str, transport: httpx.AsyncBaseTransport | None = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.transport = transport

    async def send(self, title: str, body: str, priority: str = "default", url: str | None = None) -> None:
        text = f"{title}\n\n{body}" + (f"\n{url}" if url else "")
        payload = {"chat_id": self.chat_id, "text": text, "disable_web_page_preview": True}
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S, transport=self.transport) as client:
            response = await client.post(f"https://api.telegram.org/bot{self.bot_token}/sendMessage", json=payload)
            response.raise_for_status()


async def send_all(channels: list[Channel], title: str, body: str, priority: str = "default", url: str | None = None) -> list[str]:
    """Envoie sur chaque canal ; renvoie les noms des canaux qui ont reçu le message."""
    delivered = []
    for channel in channels:
        try:
            await channel.send(title, body, priority, url)
            delivered.append(channel.name)
        except Exception as exc:  # canal injoignable, jeton refusé… : on journalise et on continue
            logger.warning(f"Notification via {channel.name} failed: {type(exc).__name__}: {exc}")
    return delivered
