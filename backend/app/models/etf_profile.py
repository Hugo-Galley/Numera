from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class EtfProfile(Base):
    __tablename__ = "etf_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    isin: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    
    # JSON encoded strings:
    # aliases: ["CW8", "WPEA", "EWLD", "LU1681043599"]
    aliases: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    
    # countries: {"USA": 71.0, "JPN": 5.4, "GBR": 3.6, "FRA": 2.8, ...}
    countries: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    
    # sectors: {"Technologie": 24.8, "Finance": 15.1, "Santé": 12.0, ...}
    sectors: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    
    # top_holdings: [{"name": "Apple", "ticker": "AAPL", "weight": 4.8}, {"name": "Microsoft", "ticker": "MSFT", "weight": 4.3}, ...]
    top_holdings: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)
