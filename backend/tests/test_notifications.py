"""Notifications push (ntfy, Telegram) : envoi unique par alerte, résumé hebdo, réglages masqués."""
import asyncio
import json
from datetime import datetime

import httpx
import pytest

import app.integrations.notifications as channels
import app.services.notifications as notif
from app.db.system_settings import get_setting, set_setting
from app.models.notification_log import NotificationLog
from app.schemas.insight import ActionItem


class FakeChannel:
    name = "fake"

    def __init__(self, fail: bool = False):
        self.sent: list[dict] = []
        self.fail = fail

    async def send(self, title, body, priority="default", url=None):
        if self.fail:
            raise httpx.TimeoutException("timeout")
        self.sent.append({"title": title, "body": body, "priority": priority, "url": url})


def _action(id_="a1", severity="medium", description="Description"):
    return ActionItem(id=id_, type="audit", severity=severity, title=f"Titre {id_}", description=description,
                      action_type="link", action_url="/audit")


@pytest.fixture()
def channel(monkeypatch):
    fake = FakeChannel()
    monkeypatch.setattr(notif, "enabled_channels", lambda db: [fake])
    return fake


def _with_actions(monkeypatch, actions):
    async def fake_actions(db):
        return list(actions)
    monkeypatch.setattr(notif, "current_actions", fake_actions)


def _run(db, now=datetime(2026, 10, 21, 10, 0)):  # un mercredi : pas de résumé hebdo
    return asyncio.run(notif.run_notifications(db, now))


def test_first_run_sends_single_hello(db_session, channel, monkeypatch):
    _with_actions(monkeypatch, [_action("a1"), _action("a2"), _action("a3", "high")])
    assert _run(db_session) == 1
    assert len(channel.sent) == 1
    assert "3" in channel.sent[0]["body"]
    assert db_session.query(NotificationLog).count() == 3
    assert get_setting(db_session, "notify.initialized") == "1"


def test_new_action_sent_once(db_session, channel, monkeypatch):
    _with_actions(monkeypatch, [_action("a1")])
    _run(db_session)
    _with_actions(monkeypatch, [_action("a1"), _action("a2", "high")])
    assert _run(db_session) == 1
    assert channel.sent[-1]["title"] == "Titre a2"
    assert channel.sent[-1]["url"] is None  # pas d'URL publique configurée
    assert _run(db_session) == 0


def test_changed_action_resent(db_session, channel, monkeypatch):
    _with_actions(monkeypatch, [_action("budget", description="80 % du budget")])
    _run(db_session)
    _with_actions(monkeypatch, [_action("budget", description="100 % du budget")])
    assert _run(db_session) == 1
    assert "100 %" in channel.sent[-1]["body"]


def test_min_severity_filters(db_session, channel, monkeypatch):
    set_setting(db_session, "notify.min_severity", "high")
    _with_actions(monkeypatch, [])
    _run(db_session)
    _with_actions(monkeypatch, [_action("m", "medium"), _action("h", "high")])
    assert _run(db_session) == 1
    assert channel.sent[-1]["title"] == "Titre h"


def test_many_new_actions_grouped(db_session, channel, monkeypatch):
    _with_actions(monkeypatch, [])
    _run(db_session)
    _with_actions(monkeypatch, [_action(f"x{i}") for i in range(6)])
    assert _run(db_session) == 1
    assert "6" in channel.sent[-1]["title"]
    assert db_session.query(NotificationLog).count() == 6


def test_public_url_builds_click_link(db_session, channel, monkeypatch):
    set_setting(db_session, "notify.public_url", "https://numera.example.org/")
    _with_actions(monkeypatch, [])
    _run(db_session)
    _with_actions(monkeypatch, [_action("a1")])
    _run(db_session)
    assert channel.sent[-1]["url"] == "https://numera.example.org/audit"


def test_failed_channel_not_logged(db_session, monkeypatch):
    failing = FakeChannel(fail=True)
    monkeypatch.setattr(notif, "enabled_channels", lambda db: [failing])
    _with_actions(monkeypatch, [_action("a1")])
    assert _run(db_session) == 0
    assert db_session.query(NotificationLog).count() == 0
    assert get_setting(db_session, "notify.initialized") is None


def test_no_channel_does_nothing(db_session, monkeypatch):
    monkeypatch.setattr(notif, "enabled_channels", lambda db: [])
    _with_actions(monkeypatch, [_action("a1")])
    assert _run(db_session) == 0


def test_mask_amounts():
    assert notif.mask_amounts("Budget 1 234,56 € dépassé") == "Budget ••• € dépassé"
    assert notif.mask_amounts("Netflix passe à 15.99 EUR") == "Netflix passe à ••• EUR"
    assert notif.mask_amounts("80 % du budget") == "80 % du budget"


def test_hide_amounts_setting(db_session, channel, monkeypatch):
    set_setting(db_session, "notify.hide_amounts", "1")
    _with_actions(monkeypatch, [])
    _run(db_session)
    _with_actions(monkeypatch, [_action("a1", description="Dépassement de 120,00 €")])
    _run(db_session)
    assert "120" not in channel.sent[-1]["body"]


def test_weekly_digest_once_per_week(db_session, channel, monkeypatch):
    set_setting(db_session, "notify.weekly_digest", "1")
    _with_actions(monkeypatch, [])
    sunday_evening = datetime(2026, 10, 25, 19, 0)
    assert asyncio.run(notif.send_weekly_digest(db_session, sunday_evening)) is True
    assert "semaine" in channel.sent[-1]["title"].lower()
    assert asyncio.run(notif.send_weekly_digest(db_session, datetime(2026, 10, 25, 21, 0))) is False
    assert asyncio.run(notif.send_weekly_digest(db_session, datetime(2026, 10, 24, 19, 0))) is False  # samedi
    assert asyncio.run(notif.send_weekly_digest(db_session, datetime(2026, 11, 1, 17, 0))) is False  # avant 18 h
    assert asyncio.run(notif.send_weekly_digest(db_session, datetime(2026, 11, 1, 18, 5))) is True


def test_weekly_digest_disabled_by_default(db_session, channel, monkeypatch):
    _with_actions(monkeypatch, [])
    assert asyncio.run(notif.send_weekly_digest(db_session, datetime(2026, 10, 25, 19, 0))) is False


def test_ntfy_channel_request():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        seen["json"] = json.loads(request.content)
        return httpx.Response(200)

    channel = channels.NtfyChannel("https://ntfy.example.org/", "numera-x", "tk_abcd", transport=httpx.MockTransport(handler))
    asyncio.run(channel.send("Budget dépassé", "Restos à 104 %", "high", "https://n.example/audit"))
    assert seen["url"] == "https://ntfy.example.org/"
    assert seen["auth"] == "Bearer tk_abcd"
    assert seen["json"] == {"topic": "numera-x", "title": "Budget dépassé", "message": "Restos à 104 %",
                            "priority": 4, "click": "https://n.example/audit"}


def test_telegram_channel_request():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["json"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True})

    channel = channels.TelegramChannel("123:ABC", "42", transport=httpx.MockTransport(handler))
    asyncio.run(channel.send("Titre", "Corps", "default", None))
    assert seen["url"] == "https://api.telegram.org/bot123:ABC/sendMessage"
    assert seen["json"]["chat_id"] == "42"
    assert seen["json"]["text"] == "Titre\n\nCorps"


def test_channel_http_error_raises():
    channel = channels.NtfyChannel("https://ntfy.sh", "t", None, transport=httpx.MockTransport(lambda r: httpx.Response(401)))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(channel.send("a", "b"))


def test_enabled_channels_from_settings(db_session):
    assert notif.enabled_channels(db_session) == []
    set_setting(db_session, "notify.ntfy.enabled", "1")
    set_setting(db_session, "notify.ntfy.topic", "numera-x")
    set_setting(db_session, "notify.telegram.enabled", "1")  # sans jeton : ignoré
    channels = notif.enabled_channels(db_session)
    assert [c.name for c in channels] == ["ntfy"]


def test_settings_masks_tokens(client, db_session):
    resp = client.put("/notifications/settings", json={
        "ntfy_enabled": True, "ntfy_topic": "numera-x", "ntfy_token": "tk_secret_abcd",
        "telegram_bot_token": "123:XYZ9", "min_severity": "high", "weekly_digest": True,
    })
    assert resp.status_code == 200, resp.text
    data = client.get("/notifications/settings").json()
    assert data["ntfy_token"] == "••••abcd"
    assert data["telegram_bot_token"] == "••••XYZ9"
    assert data["ntfy_server"] == "https://ntfy.sh"
    assert data["min_severity"] == "high" and data["weekly_digest"] is True

    client.put("/notifications/settings", json={"ntfy_token": "••••abcd", "ntfy_topic": "autre"})
    assert get_setting(db_session, "notify.ntfy.token") == "tk_secret_abcd"
    assert get_setting(db_session, "notify.ntfy.topic") == "autre"

    client.put("/notifications/settings", json={"ntfy_token": ""})
    assert not get_setting(db_session, "notify.ntfy.token")


def test_settings_reject_bad_values(client):
    assert client.put("/notifications/settings", json={"min_severity": "urgent"}).status_code == 422
    assert client.put("/notifications/settings", json={"ntfy_server": "ftp://x"}).status_code == 422


def test_test_endpoint_requires_configuration(client):
    assert client.post("/notifications/test", json={"channel": "telegram"}).status_code == 400


def test_test_endpoint_sends(client, monkeypatch):
    fake = FakeChannel()
    monkeypatch.setattr(notif, "build_channel", lambda db, name: fake)
    resp = client.post("/notifications/test", json={"channel": "ntfy"})
    assert resp.status_code == 200
    assert len(fake.sent) == 1


def test_test_endpoint_reports_failure(client, monkeypatch):
    monkeypatch.setattr(notif, "build_channel", lambda db, name: FakeChannel(fail=True))
    assert client.post("/notifications/test", json={"channel": "ntfy"}).status_code == 502


def test_real_action_center_runs(db_session, channel):
    """Sans substitution : le calcul réel du Centre d'Actions sur une base vide ne casse rien."""
    assert _run(db_session) == 1  # message de bienvenue, 0 action


def test_digest_body_sections_all_computed(db_session, monkeypatch):
    """Les sections du résumé avalent leurs erreurs : vérifier qu'aucune n'est sautée."""
    from app.domain.finance import month_label_from_date
    from app.models.account import Account
    from app.models.transaction import Transaction

    account = Account(name="Courant", type="courant", currency="EUR")
    db_session.add(account)
    db_session.flush()
    now = datetime.now()
    db_session.add(Transaction(account_id=account.id, date=now.replace(day=1), amount=42.0, type="Sortie",
                               merchant="Boulangerie", currency="EUR", original_amount=42.0,
                               month_label=month_label_from_date(now), running_balance=-42.0))
    db_session.commit()
    warnings: list[str] = []
    monkeypatch.setattr(notif.logger, "warning", lambda msg, *a, **k: warnings.append(str(msg)))

    body = asyncio.run(notif._digest_body(db_session, now))

    assert warnings == []
    assert "Ce mois-ci :" in body
    assert "Centre d'Actions :" in body
