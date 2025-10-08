from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import relationship

from app.database import Base


class SleepLog(Base):
    __tablename__ = "sleep_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    sleep_time = Column(String, nullable=False)  # "HH:MM"
    wake_time = Column(String, nullable=False)   # "HH:MM"
    duration_hours = Column(Float, nullable=False)
    evaluation = Column(String, nullable=True)
    electronics_used = Column(String, nullable=True)  # "yes" or "no"
    quality_rating = Column(Integer, nullable=True)  # 1-5
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("app.models.user.User")




