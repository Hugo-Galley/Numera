from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class NotificationLog(Base):
    """Alerte du Centre d'Actions déjà envoyée : une empreinte (id + titre + description) n'est notifiée qu'une fois."""

    __tablename__ = "notification_log"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    action_id: Mapped[str] = mapped_column(String(120), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)  # canaux ayant reçu le message, ou « init »
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
