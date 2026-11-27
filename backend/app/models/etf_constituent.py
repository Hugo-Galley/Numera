from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EtfConstituent(Base):
    """Une ligne de la composition complète d'un ETF, telle que publiée par son émetteur (poids en %)."""

    __tablename__ = "etf_constituents"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("etf_profiles.id", ondelete="CASCADE"), index=True, nullable=False)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    ticker: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    country: Mapped[str | None] = mapped_column(String(3), nullable=True)
    sector: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(64), nullable=False)
