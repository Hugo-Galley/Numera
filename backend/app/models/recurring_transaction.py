from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # Entree, Sortie, Interets
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)  # monthly, weekly, quarterly, yearly
    day_of_month: Mapped[int | None] = mapped_column(nullable=True)
    excluded_months: Mapped[str | None] = mapped_column(String(50), nullable=True)  # CSV of months (1-12) to skip
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_generated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_generate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transfer_to_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)  # virement vers ce compte

    # Asset Allocation (Sprint 4)
    asset_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    geographic_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Market & Securities (Sprint 5)
    ticker: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    isin: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    etf_profile_id: Mapped[int | None] = mapped_column(ForeignKey("etf_profiles.id", ondelete="SET NULL"), nullable=True, index=True)

    account: Mapped["Account"] = relationship("Account", foreign_keys=[account_id])
    category: Mapped["Category"] = relationship("Category")
    etf_profile: Mapped["EtfProfile"] = relationship("EtfProfile", lazy="selectin")

