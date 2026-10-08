from datetime import datetime

import httpx
import pytest

from app.core import logos
from app.models.account import Account
from app.models.recurring_transaction import RecurringTransaction


@pytest.fixture(autouse=True)
def logos_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(logos, "LOGOS_DIR", tmp_path / "logos")
    return tmp_path / "logos"


def test_search_finds_known_brands(client):
    res = client.get("/logos/search", params={"q": "clau"})
    assert res.status_code == 200
    refs = [r["ref"] for r in res.json()]
    assert "si:claude" in refs
    first = res.json()[0]
    assert {"ref", "title", "hex"} <= set(first)

    refs = [r["ref"] for r in client.get("/logos/search", params={"q": "YouTube"}).json()]
    assert refs[0] == "si:youtube"  # correspondance exacte avant les préfixes (youtubemusic…)


def test_search_empty_and_unknown(client):
    assert client.get("/logos/search", params={"q": ""}).json() == []
    assert client.get("/logos/search", params={"q": "zzzzqqqq"}).json() == []


def test_serve_simple_icon_svg(client):
    res = client.get("/logos/img/si:claude")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/svg+xml")
    assert "<path" in res.text and "fill=" in res.text


@pytest.mark.parametrize("ref", ["si:nope_nope", "file:abc.png", "../../etc/passwd", "file:../x.png", "si:"])
def test_serve_rejects_bad_refs(client, ref):
    assert client.get(f"/logos/img/{ref}").status_code in (404, 422)


def _mock_favicon(monkeypatch, content=b"\x89PNG-fake", status=200, ctype="image/png"):
    async def fake_get(self, url, **kw):
        return httpx.Response(status, content=content, headers={"content-type": ctype}, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)


def test_from_domain_stores_and_serves(client, monkeypatch, logos_dir):
    _mock_favicon(monkeypatch)
    res = client.post("/logos/from-domain", json={"domain": "https://www.Navigo.fr/tarifs?x=1"})
    assert res.status_code == 200
    ref = res.json()["ref"]
    assert ref.startswith("file:") and ref.endswith(".png")
    assert len(list(logos_dir.glob("*.png"))) == 1
    img = client.get(f"/logos/img/{ref}")
    assert img.status_code == 200 and img.content == b"\x89PNG-fake"
    assert img.headers["content-type"] == "image/png"
    # idempotent : même domaine → même fichier
    assert client.post("/logos/from-domain", json={"domain": "navigo.fr"}).json()["ref"] == ref
    assert len(list(logos_dir.glob("*.png"))) == 1


@pytest.mark.parametrize("domain", ["", "pas un domaine", "localhost", "127.0.0.1", "a/b", "evil.com@x"])
def test_from_domain_rejects_invalid(client, monkeypatch, domain):
    _mock_favicon(monkeypatch)
    assert client.post("/logos/from-domain", json={"domain": domain}).status_code == 422


def test_from_domain_upstream_failures(client, monkeypatch):
    _mock_favicon(monkeypatch, status=404)
    assert client.post("/logos/from-domain", json={"domain": "inconnu.example"}).status_code == 404
    _mock_favicon(monkeypatch, ctype="text/html")
    assert client.post("/logos/from-domain", json={"domain": "inconnu.example"}).status_code == 404
    _mock_favicon(monkeypatch, content=b"x" * 300_000)
    assert client.post("/logos/from-domain", json={"domain": "gros.example"}).status_code == 404


def test_recurrence_logo_persisted(client, db_session):
    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(acc)
    db_session.commit()
    payload = {
        "account_id": acc.id, "name": "Claude Pro", "type": "Sortie", "amount": 20.0,
        "frequency": "monthly", "day_of_month": 3, "start_date": datetime(2026, 1, 1).isoformat(),
        "logo": "si:claude",
    }
    res = client.post("/recurring-transactions/", json=payload)
    assert res.status_code == 200 and res.json()["logo"] == "si:claude"
    rid = res.json()["id"]
    assert db_session.get(RecurringTransaction, rid).logo == "si:claude"

    res = client.patch(f"/recurring-transactions/{rid}", json={"logo": "si:youtube"})
    assert res.json()["logo"] == "si:youtube"
    res = client.patch(f"/recurring-transactions/{rid}", json={"logo": None})
    assert res.json()["logo"] is None
    db_session.expire_all()
    assert db_session.get(RecurringTransaction, rid).logo is None


def test_recurrence_rejects_bad_logo(client, db_session):
    acc = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(acc)
    db_session.commit()
    payload = {
        "account_id": acc.id, "name": "X", "type": "Sortie", "amount": 1.0,
        "frequency": "monthly", "start_date": datetime(2026, 1, 1).isoformat(), "logo": "http://evil/x.png",
    }
    assert client.post("/recurring-transactions/", json=payload).status_code == 422
