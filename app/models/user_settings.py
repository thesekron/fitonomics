from __future__ import annotations

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    wake_time = Column(String, nullable=True)   # HH:MM
    sleep_time = Column(String, nullable=True)  # HH:MM
    workout_pref = Column(String, nullable=True)  # morning/day/evening
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("app.models.user.User")




