from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    monthly_limit: Mapped[float | None] = mapped_column(nullable=True)
    annual_limit: Mapped[float | None] = mapped_column(nullable=True)
    group: Mapped[str | None] = mapped_column(String(32), nullable=True)
