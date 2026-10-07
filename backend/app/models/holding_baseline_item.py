from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HoldingBaselineItem(Base):
    """Ligne de l'inventaire « Point Zéro » des positions d'un compte.

    Les positions (`portfolio_holdings`) sont recalculées à partir de cet inventaire, puis des
    opérations sur titres postérieures à `baseline_date` (voir `core/holdings.py::rebuild_holdings`).
    """

    __tablename__ = "holding_baseline_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    baseline_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    ticker: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    isin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    asset_name: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    buy_price_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    etf_profile_id: Mapped[int | None] = mapped_column(ForeignKey("etf_profiles.id", ondelete="SET NULL"), nullable=True)
