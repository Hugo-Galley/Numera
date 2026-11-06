"""Notifications dans la langue enregistrée (`notify.language`) : tâche de fond sans requête HTTP."""
import asyncio
from datetime import datetime

import pytest

import app.services.systeme.notifications as notif
from app.core.i18n import get_language, set_language
from app.db.system_settings import get_setting, set_setting
from app.models.notification_log import NotificationLog
from app.schemas.insight import ActionItem
from tests.systeme.test_notifications import FakeChannel


@pytest.fixture(autouse=True)
def _reset_language():
    set_language("fr")
    yield
    set_language("fr")


@pytest.fixture()
def channel(monkeypatch):
    fake = FakeChannel()
    monkeypatch.setattr(notif, "enabled_channels", lambda db: [fake])
    return fake


def _action(id_="a1", severity="medium"):
    # Le texte de l'action dépend de la langue courante, comme les vraies règles du Centre d'Actions
    return ActionItem(
        id=id_, type="audit", severity=severity, title=(f"Alert {id_}" if get_language() == "en" else f"Titre {id_}"),
        description="Description", action_type="link", action_url="/audit",
    )


def _with_actions(monkeypatch, actions_factory):
    async def fake_actions(db):
        return actions_factory()
    monkeypatch.setattr(notif, "current_actions", fake_actions)


def _run(db, now=datetime(2026, 10, 21, 10, 0)):
    return asyncio.run(notif.run_notifications(db, now))


def test_language_setting_defaults_to_french_and_is_saved(client, db_session):
    assert client.get("/notifications/settings").json()["language"] == "fr"
    res = client.put("/notifications/settings", json={"language": "en"})  # pas sensible : sans mot de passe
    assert res.status_code == 200 and res.json()["language"] == "en"
    assert get_setting(db_session, "notify.language") == "en"
    assert client.put("/notifications/settings", json={"language": "de"}).status_code == 422


def test_hello_message_in_english(db_session, channel, monkeypatch):
    set_setting(db_session, "notify.language", "en")
    _with_actions(monkeypatch, lambda: [_action("a1"), _action("a2")])
    assert _run(db_session) == 1
    assert channel.sent[0]["title"] == "Numera connected"
    assert channel.sent[0]["body"] == "Notifications enabled: 2 action(s) in progress in the Action Center."
    assert get_language() == "fr"  # la langue du contexte est restaurée


def test_hello_message_stays_french_by_default(db_session, channel, monkeypatch):
    _with_actions(monkeypatch, lambda: [_action("a1")])
    _run(db_session)
    assert channel.sent[0]["title"] == "Numera connecté"
    assert channel.sent[0]["body"] == "Notifications activées : 1 action(s) en cours dans le Centre d'Actions."


def test_alerts_are_sent_in_language_but_fingerprints_stay_french(db_session, channel, monkeypatch):
    _with_actions(monkeypatch, lambda: [_action("a1")])
    _run(db_session)  # accueil en français : a1 connue
    set_setting(db_session, "notify.language", "en")
    _with_actions(monkeypatch, lambda: [_action("a1"), _action("a2", "high")])
    assert _run(db_session) == 1  # a1 n'est pas renvoyée parce que la langue a changé
    assert channel.sent[-1]["title"] == "Alert a2"
    fingerprints = {row.fingerprint for row in db_session.query(NotificationLog).all()}
    assert len(fingerprints) == 2
    assert _run(db_session) == 0


def test_grouped_title_in_english(db_session, channel, monkeypatch):
    set_setting(db_session, "notify.language", "en")
    _with_actions(monkeypatch, lambda: [])
    _run(db_session)
    _with_actions(monkeypatch, lambda: [_action(f"a{i}") for i in range(6)])
    _run(db_session)
    assert channel.sent[-1]["title"] == "6 new Numera alerts"
    assert channel.sent[-1]["body"].startswith("• Alert a")


def test_digest_in_english(db_session, channel, monkeypatch):
    set_setting(db_session, "notify.language", "en")
    set_setting(db_session, "notify.weekly_digest", "1")
    _with_actions(monkeypatch, lambda: [_action("a1", "high")])

    async def fake_budget(**_):
        return {"depenses_reelles": 1234.5, "revenus_totaux": 3000}
    monkeypatch.setattr(notif, "compute_budget", fake_budget)
    assert asyncio.run(notif.send_weekly_digest(db_session, datetime(2026, 10, 25, 19, 0))) is True
    sent = channel.sent[-1]
    assert sent["title"] == "Your week with Numera"
    assert "This month: €1,234.50 of actual spending, €3,000.00 of income." in sent["body"]
    assert "Action Center: 1 action(s) in progress, 1 urgent." in sent["body"]


def test_digest_in_french_unchanged(db_session, channel, monkeypatch):
    set_setting(db_session, "notify.weekly_digest", "1")
    _with_actions(monkeypatch, lambda: [])

    async def fake_budget(**_):
        return {"depenses_reelles": 1234.5, "revenus_totaux": 3000}
    monkeypatch.setattr(notif, "compute_budget", fake_budget)
    asyncio.run(notif.send_weekly_digest(db_session, datetime(2026, 10, 25, 19, 0)))
    body = channel.sent[-1]["body"]
    assert channel.sent[-1]["title"] == "Ta semaine avec Numera"
    assert "Ce mois-ci : 1 234,50 € de dépenses réelles, 3 000,00 € de revenus." in body


def test_mask_amounts_english_formats():
    assert notif.mask_amounts("Over by €1,234.50 this month") == "Over by ••• this month"
    assert notif.mask_amounts("Netflix goes to $15.99") == "Netflix goes to •••"
    assert notif.mask_amounts("80% of budget") == "80% of budget"


def test_test_notification_follows_request_language(client, monkeypatch):
    fake = FakeChannel()
    monkeypatch.setattr(notif, "build_channel", lambda db, name: fake)
    client.post("/notifications/test", json={"channel": "ntfy"}, headers={"Accept-Language": "en"})
    assert fake.sent[-1]["title"] == "Numera test" and fake.sent[-1]["body"] == "Notifications are working."
