from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InvestmentTransaction(Base):
    __tablename__ = "investment_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    original_amount: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Asset Allocation (Sprint 4)
    asset_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    geographic_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Transfers (Sprint 4)
    is_transfer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_transfer_ignored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    linked_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True, index=True)
    recurring_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("recurring_transactions.id"), nullable=True, index=True)

    linked_transaction: Mapped["Transaction"] = relationship("Transaction", lazy="selectin", foreign_keys=[linked_transaction_id])
    recurring_transaction: Mapped["RecurringTransaction"] = relationship("RecurringTransaction", lazy="selectin")
