from datetime import date

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TelecommutingDay(Base):
    __tablename__ = "telecommuting_days"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    salary_config_id: Mapped[int] = mapped_column(ForeignKey("salary_configs.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    month_label: Mapped[str] = mapped_column(String(7), nullable=False, index=True) # e.g. "2026-06"

    config: Mapped["SalaryConfig"] = relationship("SalaryConfig")
