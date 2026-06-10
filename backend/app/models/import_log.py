from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class ImportLog(Base):
    __tablename__ = "imports_log"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    imported_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
