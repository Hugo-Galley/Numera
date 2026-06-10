from sqlalchemy import Date, Float, String
from sqlalchemy.orm import Mapped, mapped_column
from datetime import date

from app.db.base import Base

class HistoricalExchangeRate(Base):
    __tablename__ = "historical_exchange_rates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    rate: Mapped[float] = mapped_column(Float, nullable=False) # 1 EUR = rate currency
