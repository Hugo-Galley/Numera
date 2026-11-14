from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.tag import transaction_tags

if TYPE_CHECKING:
    from app.models.benefit import Benefit
    from app.models.category import Category
    from app.models.investment_transaction import InvestmentTransaction
    from app.models.merchant import Merchant
    from app.models.recurring_transaction import RecurringTransaction
    from app.models.reimbursement import ReimbursementClaim
    from app.models.tag import Tag
    from app.models.transaction_split import TransactionSplit


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    month_label: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    merchant: Mapped[str] = mapped_column(String(120), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    original_amount: Mapped[float] = mapped_column(Float, nullable=False)
    running_balance: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurring_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("recurring_transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    is_subscription_ignored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    custom_icon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    custom_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    is_transfer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_transfer_ignored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_duplicate_ignored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    linked_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    linked_investment_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("investment_transactions.id", ondelete="SET NULL", use_alter=True, name="fk_tx_linked_investment"), nullable=True, index=True)
    # Origine du lien de virement (manual | rule | recurring) et règle à l'origine
    link_origin: Mapped[str | None] = mapped_column(String(16), nullable=True)
    transfer_rule_id: Mapped[int | None] = mapped_column(ForeignKey("transfer_rules.id", ondelete="SET NULL"), nullable=True, index=True)
    # Virement récurrent à arrivée différée : date à laquelle créditer la destination (None une fois crédité)
    transfer_credit_due: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Valeurs brutes du relevé à l'import (clé de doublon, règle 4) : indépendantes des règles et des retouches manuelles
    original_merchant: Mapped[str | None] = mapped_column(String(120), nullable=True)
    original_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    merchant_id: Mapped[int | None] = mapped_column(ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True, index=True)
    # Total remboursé (Sortie) ou affecté à des créances (Entree) ; maintenu par services/reimbursements.py
    reimbursement_offset: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
    # Aide (prime d'activité, APL…) à l'origine de l'entrée ; `is_provisional` : générée au montant attendu,
    # remplacée par le vrai versement à l'import (services/budget/benefit_generation.py)
    benefit_id: Mapped[int | None] = mapped_column(ForeignKey("benefits.id", ondelete="SET NULL"), nullable=True, index=True)
    is_provisional: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    # Dépense hors norme (achat ponctuel) : reste dans les totaux, isolée dans la lecture « hors exceptionnel »
    is_exceptional: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)

    category: Mapped["Category"] = relationship("Category", lazy="selectin")
    benefit: Mapped["Benefit"] = relationship("Benefit", lazy="selectin")
    recurring_transaction: Mapped["RecurringTransaction"] = relationship("RecurringTransaction", lazy="selectin")
    linked_transaction: Mapped["Transaction"] = relationship("Transaction", remote_side=[id], post_update=True, foreign_keys=[linked_transaction_id])
    linked_investment_transaction: Mapped["InvestmentTransaction"] = relationship("InvestmentTransaction", lazy="selectin", post_update=True, foreign_keys=[linked_investment_transaction_id])
    merchant_obj: Mapped["Merchant"] = relationship("Merchant", lazy="selectin")
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary=transaction_tags, back_populates="transactions", lazy="selectin")
    splits: Mapped[list["TransactionSplit"]] = relationship(
        "TransactionSplit", lazy="selectin", cascade="all, delete-orphan", order_by="TransactionSplit.id"
    )
    claims: Mapped[list["ReimbursementClaim"]] = relationship(
        "ReimbursementClaim", lazy="selectin", viewonly=True
    )

    @property
    def linked_account_id(self) -> int | None:
        """Compte du partenaire du virement (transaction ou opération d'investissement liée)."""
        if self.linked_transaction_id is not None and self.linked_transaction is not None:
            return self.linked_transaction.account_id
        if self.linked_investment_transaction is not None:
            return self.linked_investment_transaction.account_id
        return None

    @property
    def recurring_logo(self) -> str | None:
        """Logo de la récurrence (ou de l'aide) d'origine (exposé par TransactionRead)."""
        if self.recurring_transaction and self.recurring_transaction.logo:
            return self.recurring_transaction.logo
        return self.benefit.logo if self.benefit else None

    @property
    def has_claims(self) -> bool:
        """La dépense porte au moins une créance de remboursement."""
        return bool(self.claims)

    @property
    def reimbursement_expected(self) -> float:
        """Total attendu des créances de la dépense (affichage du statut de remboursement)."""
        return round(sum(c.expected_amount for c in self.claims), 2)
