"""
Meal logging models for tracking user meal choices and ratings.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text
from app.database import Base


class MealLog(Base):
    """Log of user meal choices and ratings."""
    __tablename__ = "meal_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Meal type
    meal_type = Column(String(20), nullable=False)  # 'breakfast', 'lunch', 'dinner'
    
    # Pack or custom meal
    is_pack = Column(Boolean, default=True, nullable=False)
    pack_id = Column(String(50), nullable=True)  # ID from JSON if it's a pack
    pack_name = Column(String(100), nullable=True)  # Name for display
    
    # Custom meal fields (when is_pack = False)
    custom_description = Column(Text, nullable=True)  # What user ate
    custom_category = Column(String(20), nullable=True)  # breakfast/lunch/dinner
    
    # Health rating (for custom meals)
    health_rating = Column(String(10), nullable=True)  # 'healthy', 'normal', 'unhealthy'
    
    # Pack details (for packs)
    calories = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    prep_time = Column(Integer, nullable=True)  # in minutes
    flags = Column(String(200), nullable=True)  # tags from pack
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class UserMealSettings(Base):
    """User meal preferences and settings."""
    __tablename__ = "user_meal_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    
    # Budget preference
    budget_level = Column(String(10), nullable=False, default="mid")  # 'low', 'mid', 'high'
    
    # Notification settings
    breakfast_reminder = Column(Boolean, default=False, nullable=False)
    lunch_reminder = Column(Boolean, default=False, nullable=False)
    dinner_reminder = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
