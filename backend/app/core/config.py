from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


INSECURE_SECRET_VALUES = {
    "",
    "placeholder-key-to-be-replaced-in-env",
    "generate-a-long-random-key-here",
}
INSECURE_PASSWORD_HASH_VALUES = {
    "",
    "placeholder-hash-to-be-replaced-in-env",
    "generate-using-scripts-change-password",
}


class Settings(BaseSettings):
    app_name: str = "Suivi Budget API"
    app_env: str = "dev"
    database_url: str = "sqlite:///./data/suivi_budget.db"

    # Security
    SECRET_KEY: str = "placeholder-key-to-be-replaced-in-env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    ADMIN_USERNAME: str = "admin"
    # To generate a hash: python scripts/change_password.py your-password
    ADMIN_PASSWORD_HASH: str = "placeholder-hash-to-be-replaced-in-env"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8082"
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_SECONDS: int = 900
    LOGIN_LOCKOUT_SECONDS: int = 900

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.app_env != "prod":
            return self
        if self.SECRET_KEY in INSECURE_SECRET_VALUES or len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be a non-default value of at least 32 characters in production")
        if self.ADMIN_PASSWORD_HASH in INSECURE_PASSWORD_HASH_VALUES:
            raise ValueError("ADMIN_PASSWORD_HASH must be configured in production")
        if not self.cors_origins or "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS must list explicit origins in production")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
