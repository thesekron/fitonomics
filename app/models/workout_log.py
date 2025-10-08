from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base


class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    group = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())







