from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Association table for many-to-many relationship between Transaction and Tag
transaction_tags = Table(
    "transaction_tags",
    Base.metadata,
    Column("transaction_id", Integer, ForeignKey("transactions.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)

class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # Hex color

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        secondary=transaction_tags,
        back_populates="tags"
    )
