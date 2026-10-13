from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class MonthClosure(Base):
    """Mois revu par l'utilisateur. Marqueur non bloquant : la photo des chiffres sert à détecter une modification ultérieure."""

    __tablename__ = "month_closures"
    __table_args__ = (UniqueConstraint("year", "month", name="uq_month_closures_year_month"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    highlight: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Photo prise à la clôture
    tx_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    income: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expenses: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unresolved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Totaux par devise (JSON), sans conversion : détecte une modification sans dépendre des taux de change
    fingerprint: Mapped[str | None] = mapped_column(String, nullable=True)
