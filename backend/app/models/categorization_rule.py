from sqlalchemy import ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class CategorizationRule(Base):
    __tablename__ = "categorization_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pattern: Mapped[str] = mapped_column(String(255), nullable=False) # Case-insensitive match on merchant or note
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    transaction_type: Mapped[str | None] = mapped_column(String(32), nullable=True) # Entree, Sortie, etc.
    merchant_name: Mapped[str | None] = mapped_column(String(120), nullable=True) # Normalized merchant name
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    category: Mapped["Category"] = relationship("Category")
