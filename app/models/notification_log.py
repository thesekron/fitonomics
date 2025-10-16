from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.database import Base

class NotificationLog(Base):
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    notification_type = Column(String(50), nullable=False)  # workout, breakfast, lunch, dinner, sleep
    sent_at = Column(DateTime, nullable=False)
    responded = Column(Boolean, default=False)
    action = Column(String(50))  # logged, skipped, later
    created_at = Column(DateTime, nullable=False)
