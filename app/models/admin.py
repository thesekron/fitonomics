from __future__ import annotations

from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base


class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    name = Column(String, nullable=True)
    role = Column(String, default="admin")  # super_admin, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def is_super_admin(self) -> bool:
        return self.role == "super_admin"
    
    def can_manage_users(self) -> bool:
        return self.role in ["super_admin", "admin"]
    
    def can_manage_admins(self) -> bool:
        return self.role == "super_admin"
    
    def can_send_mass_notifications(self) -> bool:
        return self.role in ["super_admin", "admin"]
