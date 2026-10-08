from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InvestmentTransaction(Base):
    __tablename__ = "investment_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
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

    # Market & Securities (Sprint 5)
    ticker: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    isin: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Devise de `unit_price` et de `fees` (devise de cotation du titre) ; à défaut, `currency`
    price_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    fees: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Dividendes : `amount` = net reçu ; la retenue à la source (même devise que `currency`) est informative.
    withholding_tax: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Dividende réinvesti : un `achat` lié (reinvest_of_id) est généré et suivi automatiquement
    reinvested: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    reinvest_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("investment_transactions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    etf_profile_id: Mapped[int | None] = mapped_column(ForeignKey("etf_profiles.id", ondelete="SET NULL"), nullable=True, index=True)

    # Transfers (Sprint 4)
    is_transfer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_transfer_ignored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    linked_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    # Origine du lien de virement (manual | rule | recurring) et règle à l'origine
    link_origin: Mapped[str | None] = mapped_column(String(16), nullable=True)
    transfer_rule_id: Mapped[int | None] = mapped_column(ForeignKey("transfer_rules.id", ondelete="SET NULL"), nullable=True, index=True)
    recurring_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("recurring_transactions.id", ondelete="SET NULL"), nullable=True, index=True)

    linked_transaction: Mapped["Transaction"] = relationship("Transaction", lazy="selectin", foreign_keys=[linked_transaction_id])
    recurring_transaction: Mapped["RecurringTransaction"] = relationship("RecurringTransaction", lazy="selectin")
    etf_profile: Mapped["EtfProfile"] = relationship("EtfProfile", lazy="selectin")
