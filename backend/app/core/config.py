from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
