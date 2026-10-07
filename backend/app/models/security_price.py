from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class SecurityPrice(Base):
    """Cours de clôture journalier d'un titre (un par ticker et par jour), dans la devise de cotation."""

    __tablename__ = "security_prices"
    __table_args__ = (UniqueConstraint("ticker", "date", name="uq_security_prices_ticker_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="yahoo")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)
