"""Notifications de test et logos : erreurs métier des services adossés aux intégrations externes."""
import asyncio

import httpx
import pytest

from app.core.errors import BusinessRuleError, ExternalServiceError, InvalidOperationError, NotFoundError
from app.schemas.notification import NotificationTestRequest
from app.services.systeme import logos as logo_service
from app.services.systeme import notifications as notif


class _FailingChannel:
    name = "ntfy"

    async def send(self, title, body, priority="default", url=None):
        raise httpx.TimeoutException("timeout")


def test_send_test_notification_failure_is_502(db_session, monkeypatch):
    monkeypatch.setattr(notif, "build_channel", lambda db, name: _FailingChannel())
    with pytest.raises(ExternalServiceError, match="Envoi impossible"):
        asyncio.run(notif.send_test_notification(db_session, NotificationTestRequest(channel="ntfy")))


def test_send_test_notification_without_configuration_is_400(db_session):
    with pytest.raises(InvalidOperationError, match="Canal incomplet"):
        asyncio.run(notif.send_test_notification(db_session, NotificationTestRequest(channel="telegram")))


def test_logo_from_invalid_domain_is_422():
    with pytest.raises(BusinessRuleError, match="Invalid domain"):
        asyncio.run(logo_service.logo_from_domain("pas un domaine"))


def test_unknown_logo_image_is_not_found():
    with pytest.raises(NotFoundError, match="Logo not found"):
        logo_service.get_logo_image("fav-0000000000000000.png")
