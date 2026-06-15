from sqlalchemy import Column, Integer, String, DateTime, func
from app.db.base import Base

class DismissedInsight(Base):
    __tablename__ = "dismissed_insights"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False, unique=True)
    dismissed_at = Column(DateTime, default=func.now(), nullable=False)
