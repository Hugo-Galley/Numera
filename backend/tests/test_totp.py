"""Double authentification TOTP : activation, connexion en deux étapes, anti-rejeu, codes de secours."""
import time

from app.core import totp
from app.core.config import settings
from app.db.system_settings import get_setting, set_setting


def _login(client, password: str = "admin"):
    return client.post("/auth/token", data={"username": settings.ADMIN_USERNAME, "password": password})


def _enable(client) -> tuple[str, list[str]]:
    setup = client.post("/auth/totp/setup", json={"current_password": "admin"})
    assert setup.status_code == 200
    data = setup.json()
    assert data["otpauth_uri"].startswith("otpauth://totp/Numera:")
    assert data["qr_svg"].startswith("data:image/svg+xml")
    # Pas précédent : le code courant reste disponible pour la connexion qui suit
    resp = client.post("/auth/totp/enable", json={"code": totp.code_for(data["secret"], time.time() - totp.PERIOD)})
    assert resp.status_code == 200
    return data["secret"], resp.json()["recovery_codes"]


def test_rfc6238_reference_vector():
    # RFC 6238, annexe B (SHA-1, clé « 12345678901234567890 »), tronqué à 6 chiffres
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    assert totp.code_for(secret, 59) == "287082"
    assert totp.code_for(secret, 1111111109) == "081804"


def test_login_without_totp_returns_session(client):
    assert client.get("/auth/totp/status").json() == {"enabled": False, "recovery_codes_left": 0}
    assert _login(client).json()["token_type"] == "bearer"


def test_setup_requires_password(client, db_session):
    assert client.post("/auth/totp/setup", json={"current_password": "wrong"}).status_code == 400
    assert not get_setting(db_session, "totp_pending_secret")


def test_enable_refuses_wrong_code(client, db_session):
    secret = client.post("/auth/totp/setup", json={"current_password": "admin"}).json()["secret"]
    stale = totp.code_for(secret, time.time() - 10 * totp.PERIOD)
    assert client.post("/auth/totp/enable", json={"code": stale}).status_code == 400
    assert client.post("/auth/totp/enable", json={"code": "abcdef"}).status_code == 400
    assert not get_setting(db_session, "totp_secret")


def test_password_login_requires_code(client, db_session):
    secret, codes = _enable(client)
    assert len(codes) == 10
    assert client.get("/auth/totp/status").json() == {"enabled": True, "recovery_codes_left": 10}

    first = _login(client).json()
    assert first["mfa_required"] is True and "access_token" not in first

    wrong = client.post("/auth/totp/login", json={"mfa_token": first["mfa_token"], "code": "12345"})
    assert wrong.status_code == 401

    code = totp.code_for(secret)
    ok = client.post("/auth/totp/login", json={"mfa_token": first["mfa_token"], "code": code})
    assert ok.status_code == 200 and ok.json()["token_type"] == "bearer"
    assert int(get_setting(db_session, "totp_last_step")) == totp.current_step()

    # Même code rejoué : refusé
    replay = client.post("/auth/totp/login", json={"mfa_token": _login(client).json()["mfa_token"], "code": code})
    assert replay.status_code == 401


def test_mfa_token_is_not_a_session(client):
    from app.main import app
    from app.api.deps import get_current_user

    _enable(client)
    mfa_token = _login(client).json()["mfa_token"]
    app.dependency_overrides.pop(get_current_user)
    resp = client.get("/accounts", headers={"Authorization": f"Bearer {mfa_token}"})
    assert resp.status_code == 401


def test_mfa_token_invalidated_by_password_change(client, db_session):
    secret, _ = _enable(client)
    mfa_token = _login(client).json()["mfa_token"]
    set_setting(db_session, "auth_valid_after", str(int(time.time()) + 1))
    resp = client.post("/auth/totp/login", json={"mfa_token": mfa_token, "code": totp.code_for(secret)})
    assert resp.status_code == 401


def test_recovery_code_is_single_use(client):
    _, codes = _enable(client)
    mfa_token = _login(client).json()["mfa_token"]
    assert client.post("/auth/totp/login", json={"mfa_token": mfa_token, "code": codes[0].upper()}).status_code == 200
    assert client.get("/auth/totp/status").json()["recovery_codes_left"] == 9
    mfa_token = _login(client).json()["mfa_token"]
    assert client.post("/auth/totp/login", json={"mfa_token": mfa_token, "code": codes[0]}).status_code == 401


def test_code_step_is_rate_limited(client):
    _enable(client)
    mfa_token = _login(client).json()["mfa_token"]
    for _ in range(settings.LOGIN_MAX_ATTEMPTS):
        assert client.post("/auth/totp/login", json={"mfa_token": mfa_token, "code": "abcde-fghij"}).status_code == 401
    assert client.post("/auth/totp/login", json={"mfa_token": mfa_token, "code": "abcde-fghij"}).status_code == 429


def test_disable_requires_password_and_code(client, db_session):
    secret, codes = _enable(client)
    assert client.post("/auth/totp/disable", json={"current_password": "wrong", "code": codes[0]}).status_code == 400
    assert client.post("/auth/totp/disable", json={"current_password": "admin", "code": "nope"}).status_code == 400
    assert client.post("/auth/totp/disable", json={"current_password": "admin", "code": codes[0]}).status_code == 200
    assert not get_setting(db_session, "totp_secret")
    assert _login(client).json()["token_type"] == "bearer"


def test_regenerate_recovery_codes(client):
    secret, old = _enable(client)
    resp = client.post("/auth/totp/recovery-codes", json={"code": totp.code_for(secret)})
    assert resp.status_code == 200
    new = resp.json()["recovery_codes"]
    assert set(new).isdisjoint(old)
    mfa_token = _login(client).json()["mfa_token"]
    assert client.post("/auth/totp/login", json={"mfa_token": mfa_token, "code": old[1]}).status_code == 401
