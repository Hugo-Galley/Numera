from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.tag import transaction_tags


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    month_label: Mapped[str] = mapped_column(String(20), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    merchant: Mapped[str] = mapped_column(String(120), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    original_amount: Mapped[float] = mapped_column(Float, nullable=False)
    running_balance: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurring_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("recurring_transactions.id"), nullable=True, index=True)
    is_subscription_ignored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    custom_icon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    custom_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_transfer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_transfer_ignored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_duplicate_ignored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    linked_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True, index=True)
    linked_investment_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("investment_transactions.id"), nullable=True, index=True)

    category: Mapped["Category"] = relationship("Category", lazy="selectin")
    recurring_transaction: Mapped["RecurringTransaction"] = relationship("RecurringTransaction", lazy="selectin")
    linked_transaction: Mapped["Transaction"] = relationship("Transaction", remote_side=[id], post_update=True, foreign_keys=[linked_transaction_id])
    linked_investment_transaction: Mapped["InvestmentTransaction"] = relationship("InvestmentTransaction", lazy="selectin", foreign_keys=[linked_investment_transaction_id])
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary=transaction_tags, back_populates="transactions", lazy="selectin")
