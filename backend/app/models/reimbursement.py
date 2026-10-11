from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow_naive
from app.db.base import Base


class ReimbursementClaim(Base):
    """Créance : une part d'une Sortie qu'un tiers doit rembourser."""

    __tablename__ = "reimbursement_claims"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    debtor: Mapped[str] = mapped_column(String(120), nullable=False)
    expected_amount: Mapped[float] = mapped_column(Float, nullable=False)  # devise du compte de la dépense
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)

    allocations: Mapped[list["ReimbursementAllocation"]] = relationship(
        "ReimbursementAllocation", back_populates="claim", cascade="all, delete-orphan", lazy="selectin"
    )


class ReimbursementAllocation(Base):
    """Part d'une Entree affectée à une créance."""

    __tablename__ = "reimbursement_allocations"
    __table_args__ = (UniqueConstraint("claim_id", "entree_transaction_id", name="uq_reimbursement_allocation"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("reimbursement_claims.id", ondelete="CASCADE"), index=True)
    entree_transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)

    claim: Mapped[ReimbursementClaim] = relationship("ReimbursementClaim", back_populates="allocations")
