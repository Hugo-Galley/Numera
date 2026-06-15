from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True) # Canonical name
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    
    category: Mapped["Category"] = relationship("Category")
    aliases: Mapped[list["MerchantAlias"]] = relationship("MerchantAlias", back_populates="merchant", cascade="all, delete-orphan")

class MerchantAlias(Base):
    __tablename__ = "merchant_aliases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    label: Mapped[str] = mapped_column(String(120), unique=True, index=True) # Original label to match
    
    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="aliases")
