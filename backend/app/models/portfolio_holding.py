from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow_naive
from app.db.base import Base


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    
    ticker: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    isin: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    asset_name: Mapped[str] = mapped_column(String(120), nullable=False)
    
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    buy_price_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    # Coût de revient total en EUR, aux taux de change des dates d'achat (calculé par rebuild_holdings)
    cost_basis_eur: Mapped[float | None] = mapped_column(Float, nullable=True)

    etf_profile_id: Mapped[int | None] = mapped_column(ForeignKey("etf_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)

    account = relationship("Account", lazy="selectin")
    etf_profile = relationship("EtfProfile", lazy="selectin")
