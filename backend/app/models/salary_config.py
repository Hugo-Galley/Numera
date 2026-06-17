from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SalaryConfig(Base):
    __tablename__ = "salary_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    salary_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    ticket_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    net_salary: Mapped[float] = mapped_column(Float, nullable=False)
    ticket_value: Mapped[float] = mapped_column(Float, nullable=False, default=10.50)
    ticket_employee_share: Mapped[float] = mapped_column(Float, nullable=False, default=4.20)
    salary_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    ticket_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    salary_recurring_id: Mapped[int | None] = mapped_column(ForeignKey("recurring_transactions.id"), nullable=True)
    ticket_recurring_id: Mapped[int | None] = mapped_column(ForeignKey("recurring_transactions.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    salary_account: Mapped["Account"] = relationship("Account", foreign_keys=[salary_account_id])
    ticket_account: Mapped["Account"] = relationship("Account", foreign_keys=[ticket_account_id])
    salary_category: Mapped["Category"] = relationship("Category", foreign_keys=[salary_category_id])
    ticket_category: Mapped["Category"] = relationship("Category", foreign_keys=[ticket_category_id])
