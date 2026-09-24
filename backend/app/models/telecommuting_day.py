from datetime import date

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TelecommutingDay(Base):
    __tablename__ = "telecommuting_days"
    __table_args__ = (
        UniqueConstraint("salary_config_id", "date", name="uq_telecommuting_config_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    salary_config_id: Mapped[int] = mapped_column(ForeignKey("salary_configs.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    month_label: Mapped[str] = mapped_column(String(7), nullable=False, index=True) # e.g. "2026-06"

    config: Mapped["SalaryConfig"] = relationship("SalaryConfig")
