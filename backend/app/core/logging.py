import logging
import re
import sys

from app.core.config import settings

# Jeton du bot Telegram, présent dans l'URL de l'API (`/bot<id>:<jeton>/…`)
_BOT_TOKEN = re.compile(r"bot\d+:[\w-]+")


class RedactSecretsFilter(logging.Filter):
    """Masque les secrets qui transiteraient dans un message de log (URL Telegram notamment)."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = _BOT_TOKEN.sub("bot<redacted>", message)
        if redacted != message:
            record.msg, record.args = redacted, None
        return True


def setup_logging() -> None:
    # Set logging level
    log_level = logging.INFO
    if settings.app_env == "dev":
        log_level = logging.DEBUG

    # Define log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    for handler in logging.getLogger().handlers:
        if not any(isinstance(f, RedactSecretsFilter) for f in handler.filters):
            handler.addFilter(RedactSecretsFilter())

    # httpx journalise chaque requête avec son URL complète
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
