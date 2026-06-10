from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_zero_point: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
