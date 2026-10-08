from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class TransferRule(Base):
    """Règle de virement interne : sorties du compte source ↔ entrées du compte destination."""

    __tablename__ = "transfer_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    dest_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    pattern: Mapped[str | None] = mapped_column(String(255), nullable=True)  # insensible à la casse, sur marchand/note de la sortie
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)  # devise du compte source
    amount_tolerance_pct: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    day_tolerance: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
