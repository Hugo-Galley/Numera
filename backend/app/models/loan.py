from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Loan(Base):
    """Paramètres d'un crédit, rattaché à un compte de type `credit` (valeur = −capital restant dû)."""

    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="autre")
    principal: Mapped[float] = mapped_column(Float, nullable=False)
    annual_rate_pct: Mapped[float] = mapped_column(Float, nullable=False)
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)  # date de la première échéance
    insurance_monthly: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    account: Mapped["Account"] = relationship("Account", lazy="selectin")
    prepayments: Mapped[list["LoanPrepayment"]] = relationship(
        "LoanPrepayment", lazy="selectin", cascade="all, delete-orphan", passive_deletes=True,
        order_by="LoanPrepayment.date",
    )


class LoanPrepayment(Base):
    """Remboursement anticipé réellement effectué."""

    __tablename__ = "loan_prepayments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # reduce_duration | reduce_payment
