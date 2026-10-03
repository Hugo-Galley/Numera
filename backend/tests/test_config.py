import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_placeholder_secrets():
    with pytest.raises(ValidationError):
        Settings(
            app_env="prod",
            SECRET_KEY="placeholder-key-to-be-replaced-in-env",
            ADMIN_PASSWORD_HASH="$2b$12$valid-looking-hash",
            CORS_ORIGINS="https://numera.example",
        )


def test_production_requires_explicit_cors_origins():
    with pytest.raises(ValidationError):
        Settings(
            app_env="prod",
            SECRET_KEY="a" * 32,
            ADMIN_PASSWORD_HASH="$2b$12$valid-looking-hash",
            CORS_ORIGINS="*",
        )


@pytest.mark.parametrize("app_env", ["dev", "prod", "staging"])
def test_secret_key_placeholder_or_short_is_rejected_outside_test(app_env):
    for bad in ("", "placeholder-key-to-be-replaced-in-env", "too-short"):
        with pytest.raises(ValidationError):
            Settings(
                app_env=app_env,
                SECRET_KEY=bad,
                ADMIN_PASSWORD_HASH="$2b$12$valid-looking-hash",
                CORS_ORIGINS="https://numera.example",
            )


def test_dev_accepts_strong_secret_without_prod_only_requirements():
    settings = Settings(app_env="dev", SECRET_KEY="a" * 32)
    assert settings.app_env == "dev"
