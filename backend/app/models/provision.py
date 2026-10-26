from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow_naive
from app.db.base import Base


class Provision(Base):
    """Grosse dépense périodique à anticiper (taxe foncière, assurance, vacances…).

    Purement prévisionnel : aucune transaction n'est créée. `due_date` est une échéance de
    référence, les suivantes s'en déduisent tous les `interval_months` (`core/provisions.py`).
    """

    __tablename__ = "provisions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)  # EUR, par échéance
    interval_months: Mapped[int] = mapped_column(Integer, nullable=False, default=12, server_default="12")
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Catégorie de la dépense réelle : sert à retrouver le dernier paiement
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    # Compte où l'argent est mis de côté : son solde mesure la constitution des provisions qui y sont rattachées
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)

    category: Mapped["Category"] = relationship("Category", lazy="selectin")
    account: Mapped["Account"] = relationship("Account", lazy="selectin")
