from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TransactionSplit(Base):
    """Part d'une dépense affectée à une catégorie. La somme des parts égale `transactions.amount`.

    Seules les répartitions par catégorie lisent les parts (`api/analytics/utils.py::category_lines`) ;
    la transaction garde la catégorie de sa plus grosse part pour tout le reste.
    """

    __tablename__ = "transaction_splits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), index=True, nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    category: Mapped["Category"] = relationship("Category", lazy="selectin")
