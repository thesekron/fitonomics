# app/models/user.py
from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(Integer, unique=True, index=True)
    name = Column(String)
    language = Column(String, default="ru")
    # profile
    age = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)  # cm
    weight = Column(Integer, nullable=True)  # kg
    budget = Column(String, nullable=True)  # low/mid/high
    reminder_time = Column(String, nullable=True)  # morning/day/evening
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())