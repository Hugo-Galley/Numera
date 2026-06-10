from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # Entree, Sortie, Interets
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)  # monthly, weekly, quarterly, yearly
    day_of_month: Mapped[int | None] = mapped_column(nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_generated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_generate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Asset Allocation (Sprint 4)
    asset_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    geographic_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    account: Mapped["Account"] = relationship("Account")
    category: Mapped["Category"] = relationship("Category")
