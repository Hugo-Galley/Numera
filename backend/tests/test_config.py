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
