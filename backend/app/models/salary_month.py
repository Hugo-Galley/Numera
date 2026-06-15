from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SalaryMonth(Base):
    __tablename__ = "salary_months"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    salary_config_id: Mapped[int] = mapped_column(ForeignKey("salary_configs.id"), nullable=False)
    month_label: Mapped[str] = mapped_column(String(7), nullable=False, index=True) # e.g. "2026-06"
    salary_date: Mapped[date] = mapped_column(Date, nullable=False)
    ticket_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    config: Mapped["SalaryConfig"] = relationship("SalaryConfig")
