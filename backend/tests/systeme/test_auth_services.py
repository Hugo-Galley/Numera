"""Services d'authentification testés sans HTTP : erreurs métier typées au lieu de HTTPException."""
from types import SimpleNamespace

import pytest

from app.core.errors import AuthenticationError, ConflictError, InvalidOperationError, NotFoundError, RateLimitedError
from app.core.login_rate_limit import login_rate_limiter
from app.schemas.auth import CodeBody, DisableBody, ReauthBody, TotpSetupBody
from app.services.systeme import auth, passkeys, totp


def _request():
    return SimpleNamespace(client=SimpleNamespace(host="9.9.9.9"), headers={"user-agent": "pytest"})


def test_enable_without_pending_setup_is_a_400_business_error(db_session):
    with pytest.raises(InvalidOperationError):
        totp.enable(db_session, CodeBody(code="000000"))


def test_disable_with_wrong_password_is_refused(db_session):
    with pytest.raises(InvalidOperationError, match="Mot de passe"):
        totp.disable(db_session, DisableBody(current_password="faux", code="000000"))


def test_setup_twice_conflicts(db_session):
    totp.setup(db_session, TotpSetupBody(current_password="admin"), "admin")
    totp.enable(db_session, CodeBody(code=_current_code(db_session)))
    with pytest.raises(ConflictError):
        totp.setup(db_session, TotpSetupBody(current_password="admin"), "admin")


def _current_code(db):
    from app.core import totp as core_totp
    from app.db.system_settings import get_setting

    return core_totp.code_for(get_setting(db, totp.PENDING_KEY_SETTING))


def test_login_with_bad_password_is_401_with_www_authenticate(db_session):
    with pytest.raises(AuthenticationError) as caught:
        auth.login(db_session, _request(), "admin", "mauvais")
    assert caught.value.status_code == 401
    assert caught.value.headers == {"WWW-Authenticate": "Bearer"}


def test_login_rate_limited_is_429_with_retry_after(db_session):
    for _ in range(50):
        login_rate_limiter.record_failure("9.9.9.9:admin")
    with pytest.raises(RateLimitedError) as caught:
        auth.login(db_session, _request(), "admin", "admin")
    assert caught.value.status_code == 429
    assert "Retry-After" in caught.value.headers
    login_rate_limiter.reset("9.9.9.9:admin")


def test_deleting_an_unknown_passkey_is_a_404(db_session):
    with pytest.raises(NotFoundError):
        passkeys.delete_passkey(db_session, "inconnue", ReauthBody(current_password="admin"))
